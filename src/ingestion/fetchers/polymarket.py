import json
import logging

import httpx

from src.ingestion.fetchers.base import retry

logger = logging.getLogger(__name__)

GAMMA_API_EVENTS = "https://gamma-api.polymarket.com/events"
GAMMA_API_SEARCH = "https://gamma-api.polymarket.com/public-search"

# Targeted searches for gold-relevant events
GOLD_MACRO_SEARCHES = [
    "gold+price",
    "federal+reserve+rate+cut",
    "tariff+trade",
    "inflation+cpi",
    "recession+economy",
]

GOLD_MACRO_TAGS = {
    "Fed",
    "Economy",
    "Taxes",
    "Geopolitics",
    "Gaza",
    "Ukraine",
    "Trump Presidency",
    "World",
}

GOLD_MACRO_KEYWORDS = [
    "gold",
    "fed rate",
    "rate cut",
    "tariff",
    "trade deal",
    "inflation",
    "cpi",
    "recession",
    "ceasefire",
    "sanction",
    "interest rate",
    "oil price",
]

EXCLUDED_CATEGORIES = {
    "Sports",
    "Soccer",
    "Crypto",
    "Movies",
    "Culture",
    "Gaming",
    "Hide From New",
    "Serie A",
    "Basketball",
    "Counter-Strike",
    "Tennis",
}


class PolymarketFetcher:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)

    @retry(max_retries=2)
    async def fetch(self) -> dict:
        """Returns {"gold_macro": [...], "market_movers": [...]}"""
        try:
            gold_macro = await self._fetch_gold_macro_events()
            market_movers = await self._fetch_market_movers()
            return {"gold_macro": gold_macro, "market_movers": market_movers}
        except Exception:
            logger.warning("Error fetching Polymarket data", exc_info=True)
            return {"gold_macro": [], "market_movers": []}
        finally:
            await self.client.aclose()

    async def _fetch_gold_macro_events(self) -> list[dict]:
        from src.config import Settings

        settings = Settings()
        search_events = []
        for query in GOLD_MACRO_SEARCHES:
            search_events.extend(await self._search_events(query))
        active = await self._fetch_active_events()
        keyword_events = [e for e in active if self._matches_gold_macro(e)]
        all_events = self._deduplicate_by_slug(search_events + keyword_events)
        filtered = self._filter_by_move(
            all_events,
            min_volume=settings.polymarket_gold_min_volume,
            min_change=settings.polymarket_gold_min_change,
        )
        return [self._extract_event_fields(e) for e in filtered]

    async def _fetch_market_movers(self) -> list[dict]:
        from src.config import Settings

        settings = Settings()
        raw = await self._fetch_active_events()
        cleaned = [e for e in raw if not self._is_excluded_category(e)]
        filtered = self._filter_by_move(
            cleaned,
            min_volume=settings.polymarket_mover_min_volume,
            min_change=settings.polymarket_mover_min_change,
        )
        return [self._extract_event_fields(e) for e in filtered]

    async def _fetch_active_events(self) -> list[dict]:
        logger.debug("→ Polymarket Gamma /events")
        resp = await self.client.get(
            GAMMA_API_EVENTS,
            params={"limit": 100, "closed": "false"},  # NOT active=True
        )
        resp.raise_for_status()
        return resp.json()

    async def _search_events(self, query: str) -> list[dict]:
        try:
            logger.debug("→ Polymarket Gamma /search?q=%s", query)
            resp = await self.client.get(
                GAMMA_API_SEARCH,
                params={"q": query, "limit_per_type": 20},
            )
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, dict) and "events" in data:
                return data["events"]
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning("Failed to search events for query '%s': %s", query, e)
            return []

    def _is_excluded_category(self, event: dict) -> bool:
        tag = self._get_tag_label(event)
        if tag and tag in EXCLUDED_CATEGORIES:
            return True
        return False

    def _matches_gold_macro(self, event: dict) -> bool:
        tag = self._get_tag_label(event)
        if tag and tag in GOLD_MACRO_TAGS:
            return True
        title = event.get("title", "").lower()
        question = (event.get("question") or "").lower()
        for kw in GOLD_MACRO_KEYWORDS:
            if kw in title or kw in question:
                return True
        return False

    def _get_tag_label(self, event: dict) -> str | None:
        tags = event.get("tags") or []
        for t in tags:
            if isinstance(t, dict) and t.get("label"):
                return t["label"]
            elif isinstance(t, str) and t.strip():
                return t.strip()
        return None

    def _deduplicate_by_slug(self, events: list[dict]) -> list[dict]:
        seen: set[str] = set()
        result: list[dict] = []
        for e in events:
            slug = e.get("slug") or e.get("id")
            if slug and slug not in seen:
                seen.add(slug)
                result.append(e)
        return result

    def _filter_by_move(
        self, events: list[dict], min_volume: float = 50000, min_change: float = 5.0
    ) -> list[dict]:
        filtered: list[dict] = []
        for e in events:
            markets = e.get("markets", [])
            if not markets:
                continue
            total_vol = 0.0
            for m in markets:
                vol_str = m.get("volume24hr") or m.get("volumeNum", "0")
                try:
                    total_vol += float(vol_str) if vol_str else 0.0
                except (ValueError, TypeError):
                    pass
            first = markets[0]
            dc = first.get("oneDayPriceChange")
            change_pct = 0.0
            if dc is not None:
                try:
                    change_pct = abs(float(dc) * 100)
                except (ValueError, TypeError):
                    pass
            if change_pct > min_change and total_vol > min_volume:
                filtered.append(e)
        return filtered

    def _extract_event_fields(self, event: dict) -> dict:
        slug = event.get("slug") or str(event.get("id", ""))
        title = event.get("title", "")
        question = event.get("question")
        description = event.get("description")
        markets = event.get("markets", [])
        volume_24h = 0.0
        liquidity = 0.0
        one_day_price_change = None
        one_hour_price_change = None
        outcome_prices = None
        if markets:
            first_market = markets[0]
            outcome_prices = first_market.get("outcomePrices")
            total_vol = 0.0
            for m in markets:
                vol_str = m.get("volume24hr") or m.get("volumeNum", "0")
                try:
                    total_vol += float(vol_str) if vol_str else 0.0
                except (ValueError, TypeError):
                    pass
            volume_24h = total_vol
            liq_str = first_market.get("liquidityNum", "0")
            try:
                liquidity = float(liq_str) if liq_str else 0.0
            except (ValueError, TypeError):
                liquidity = 0.0
            day_change = first_market.get("oneDayPriceChange")
            hour_change = first_market.get("oneHourPriceChange")
            try:
                one_day_price_change = (
                    float(day_change) * 100 if day_change is not None else None
                )  # DECIMAL TO PERCENT
            except (ValueError, TypeError):
                one_day_price_change = None
            try:
                one_hour_price_change = (
                    float(hour_change) * 100 if hour_change is not None else None
                )  # DECIMAL TO PERCENT
            except (ValueError, TypeError):
                one_hour_price_change = None
        category = self._get_tag_label(event)

        market_questions = None
        if markets:
            items = []
            for m in markets:
                q = m.get("question", "")
                if not q:
                    continue
                raw_prices = m.get("outcomePrices", "[]")
                try:
                    prices = (
                        json.loads(raw_prices)
                        if isinstance(raw_prices, str)
                        else raw_prices
                    )
                except (ValueError, TypeError):
                    prices = []
                yes_price = None
                if isinstance(prices, list) and len(prices) >= 1:
                    try:
                        yes_price = round(float(prices[0]) * 100, 1)
                    except (ValueError, TypeError):
                        pass
                items.append({"q": q, "p": yes_price})
            if items:
                market_questions = json.dumps(items, ensure_ascii=False)

        clob_token_id_yes = None
        condition_id = None
        if markets:
            first_market = markets[0]
            raw_token_ids = first_market.get("clobTokenIds", "[]")
            try:
                token_ids = (
                    json.loads(raw_token_ids)
                    if isinstance(raw_token_ids, str)
                    else raw_token_ids
                )
                if isinstance(token_ids, list) and len(token_ids) >= 1:
                    clob_token_id_yes = token_ids[0]
            except (ValueError, TypeError):
                pass
            condition_id = first_market.get("conditionId")

        return {
            "slug": slug,
            "title": title,
            "question": question,
            "description": description,
            "outcome_prices": outcome_prices,
            "volume_24h": volume_24h,
            "liquidity": liquidity,
            "one_day_price_change": one_day_price_change,
            "one_hour_price_change": one_hour_price_change,
            "category": category,
            "condition_id": condition_id,
            "clob_token_id_yes": clob_token_id_yes,
            "market_questions": market_questions,
        }
