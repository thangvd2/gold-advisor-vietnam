"""PNJ gold price scraper — JSON API via httpx GET.

Discovered: PNJ exposes a REST API at edge-api.pnj.io/ecom-frontend/v1/get-gold-price.
Response values are in unit of 1,000 VND/chỉ; multiply by 10,000 to get VND/lượng.
"""

import logging
import re
from datetime import datetime, timezone

import httpx

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

URL = "https://edge-api.pnj.io/ecom-frontend/v1/get-gold-price?zone=00"
FALLBACK_URL = "https://www.pnj.com.vn/blog/gia-vang/?r={timestamp}"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VND_LUONG_PER_NGHIN_CHI = 10_000

TIMESTAMP_PATTERN = re.compile(
    r"(\d{1,2})/(\d{1,2})/(\d{4})\s+(\d{1,2}):(\d{2}):(\d{2})"
)
SJC_BAR_CODES = {"SJC"}
RING_GOLD_CODES = {"N24K"}


def _parse_timestamp(raw: str) -> datetime | None:
    match = TIMESTAMP_PATTERN.search(raw)
    if not match:
        return None
    day, month, year, hour, minute, second = (int(g) for g in match.groups())
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)


class PNJScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "pnj"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={
                    "User-Agent": USER_AGENT,
                    "Referer": "https://www.pnj.com.vn/blog/gia-vang/",
                    "Origin": "https://www.pnj.com.vn",
                },
                timeout=10.0,
            ) as client:
                response = await client.get(URL)
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("PNJ scraper HTTP error: %s", exc)
            return []

        try:
            body = response.json()
        except Exception as exc:
            logger.error("PNJ scraper JSON parse error: %s", exc)
            return []

        price_items = body.get("data", [])
        if not price_items:
            logger.warning("PNJ: no price data in API response")
            return []

        timestamp = _parse_timestamp(body.get("updateDate", "")) or datetime.now(
            timezone.utc
        )

        prices: list[FetchedPrice] = []

        for item in price_items:
            code = item.get("masp", "")
            if code in SJC_BAR_CODES:
                product_type = "sjc_bar"
            elif code in RING_GOLD_CODES:
                product_type = "ring_gold"
            else:
                continue

            try:
                buy = float(item["giamua"]) * VND_LUONG_PER_NGHIN_CHI
                sell = float(item["giaban"]) * VND_LUONG_PER_NGHIN_CHI
            except (KeyError, ValueError, TypeError):
                logger.warning("PNJ: failed to parse prices for '%s'", code)
                continue

            prices.append(
                FetchedPrice(
                    source="pnj",
                    product_type=product_type,
                    buy_price=buy,
                    sell_price=sell,
                    price_vnd=buy,
                    currency="VND",
                    timestamp=timestamp,
                )
            )

        return prices
