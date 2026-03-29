"""SJC gold price scraper — JSON API via httpx POST.

Discovered: sjc.com.vn exposes a clean JSON API at
/GoldPrice/Services/PriceService.ashx (POST, no params required).
Returns {success, latestDate, data: [{TypeName, BuyValue, SellValue, ...}]}.
BuyValue/SellValue are already in VND/lượng — no unit conversion needed.
"""

import logging
import re
from datetime import datetime, timezone

import httpx

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

URL = "https://sjc.com.vn/GoldPrice/Services/PriceService.ashx"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
TIMESTAMP_PATTERN = re.compile(r"(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})")
SJC_BAR_PATTERN = re.compile(r"Vàng\s+SJC", re.IGNORECASE)
RING_GOLD_PATTERN = re.compile(r"Vàng\s+nhẫn\s+SJC", re.IGNORECASE)


def _parse_timestamp(raw: str) -> datetime | None:
    match = TIMESTAMP_PATTERN.search(raw)
    if not match:
        return None
    hour, minute, day, month, year = (int(g) for g in match.groups())
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


class SJCScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "sjc"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": USER_AGENT,
                    "X-Requested-With": "XMLHttpRequest",
                    "Referer": "https://sjc.com.vn/",
                },
                timeout=10.0,
            ) as client:
                logger.debug("→ SJC %s", URL)
                response = await client.post(URL)
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("SJC scraper HTTP error: %s", exc)
            return []

        try:
            body = response.json()
        except Exception as exc:
            logger.error("SJC scraper JSON parse error: %s", exc)
            return []

        if not body.get("success") or not body.get("data"):
            logger.warning("SJC: no price data in API response")
            return []

        timestamp = _parse_timestamp(body.get("latestDate", "")) or datetime.now(
            timezone.utc
        )

        seen_types: set[str] = set()
        prices: list[FetchedPrice] = []

        for item in body["data"]:
            type_name = item.get("TypeName", "")
            if SJC_BAR_PATTERN.search(type_name):
                product_type = "sjc_bar"
            elif RING_GOLD_PATTERN.search(type_name):
                product_type = "ring_gold"
            else:
                continue

            if product_type in seen_types:
                continue
            seen_types.add(product_type)

            try:
                buy = float(item["BuyValue"])
                sell = float(item["SellValue"])
            except (KeyError, ValueError, TypeError):
                logger.warning("SJC: failed to parse prices for '%s'", type_name)
                continue

            prices.append(
                FetchedPrice(
                    source="sjc",
                    product_type=product_type,
                    buy_price=buy,
                    sell_price=sell,
                    price_vnd=buy,
                    currency="VND",
                    timestamp=timestamp,
                )
            )

        return prices
