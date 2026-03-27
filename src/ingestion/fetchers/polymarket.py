import logging
from datetime import datetime, timezone

import httpx

from src.ingestion.fetchers.base import retry

logger = logging.getLogger(__name__)

GAMMA_API_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_API_SEARCH = "https://gamma-api.polymarket.com/public-search"
SEARCH_TERMS = "gold+price+federal+reserve+tariff+inflation"


class PolymarketFetcher:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(max_retries=2)
    async def fetch(self) -> list[dict]:
        try:
            events = await self._fetch_all_events()
            return events
        except Exception:
            logger.warning("Error fetching Polymarket data", exc_info=True)
            return []
        finally:
            await self.client.aclose()

    async def _fetch_all_events(self) -> list[dict]:
        active_events = await self._fetch_active_events()
        search_events = await self._search_events()
        all_events = active_events + search_events
        deduped = self._deduplicate_by_slug(all_events)
        filtered = self._filter_by_volume(deduped)
        return [self._extract_event_fields(e) for e in filtered]

    async def _fetch_active_events(self) -> list[dict]:
        try:
            resp = await self.client.get(
                GAMMA_API_EVENTS,
                params={"limit": 100, "active": "True"},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.warning("Failed to fetch active events: %s", e)
            return []

    async def _search_events(self) -> list[dict]:
        try:
            resp = await self.client.get(
                GAMMA_API_SEARCH,
                params={"q": SEARCH_TERMS, "limit_per_type": 20},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "events" in data:
                return data["events"]
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Failed to search events: %s", e)
            return []

    def _deduplicate_by_slug(self, events: list[dict]) -> list[dict]:
        seen = set()
        result = []
        for e in events:
            slug = e.get("slug") or e.get("id")
            if slug and slug not in seen:
                seen.add(slug)
                result.append(e)
        return result

    def _filter_by_volume(
        self, events: list[dict], min_volume: float = 100000
    ) -> list[dict]:
        filtered = []
        for e in events:
            markets = e.get("markets", [])
            has_high_volume = False
            for m in markets:
                volume_str = m.get("volumeNum", "0")
                try:
                    volume = float(volume_str) if volume_str else 0.0
                except (ValueError, TypeError):
                    volume = 0.0
                if volume > min_volume:
                    has_high_volume = True
                    break
            if has_high_volume:
                filtered.append(e)
        return filtered

    def _extract_event_fields(self, event: dict) -> dict:
        slug = event.get("slug") or str(event.get("id", ""))
        title = event.get("title", "")
        question = event.get("question")
        markets = event.get("markets", [])
        outcome_prices = None
        volume_24h = 0.0
        liquidity = 0.0
        one_day_price_change = None
        one_hour_price_change = None
        if markets:
            first_market = markets[0]
            outcome_prices = first_market.get("outcomePrices")
            volume_str = first_market.get("volume24hr") or first_market.get(
                "volumeNum", "0"
            )
            try:
                volume_24h = float(volume_str) if volume_str else 0.0
            except (ValueError, TypeError):
                volume_24h = 0.0
            liquidity_str = first_market.get("liquidityNum", "0")
            try:
                liquidity = float(liquidity_str) if liquidity_str else 0.0
            except (ValueError, TypeError):
                liquidity = 0.0
            day_change = first_market.get("oneDayPriceChange")
            hour_change = first_market.get("oneHourPriceChange")
            try:
                one_day_price_change = (
                    float(day_change) if day_change is not None else None
                )
            except (ValueError, TypeError):
                one_day_price_change = None
            try:
                one_hour_price_change = (
                    float(hour_change) if hour_change is not None else None
                )
            except (ValueError, TypeError):
                one_hour_price_change = None
        tags = event.get("tags") or []
        categories = event.get("categories") or []
        category = tags[0] if tags else (categories[0] if categories else None)
        if isinstance(category, dict):
            category = category.get("name") or category.get("slug")
        return {
            "slug": slug,
            "title": title,
            "question": question,
            "outcome_prices": outcome_prices,
            "volume_24h": volume_24h,
            "liquidity": liquidity,
            "one_day_price_change": one_day_price_change,
            "one_hour_price_change": one_hour_price_change,
            "category": category,
        }
