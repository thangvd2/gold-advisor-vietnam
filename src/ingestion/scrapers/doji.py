"""DOJI gold price scraper — static HTML via httpx + BeautifulSoup."""

import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

URL = "https://giavang.doji.vn"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VND_LUONG_PER_NGHIN_CHI = 10_000

SJC_PATTERN = re.compile(r"\bSJC\b", re.IGNORECASE)
RING_GOLD_PATTERN = re.compile(r"NHẪN\s+TRÒN\s+9999", re.IGNORECASE)
TIMESTAMP_PATTERN = re.compile(
    r"Cập nhập lúc:\s*(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})"
)


def _parse_timestamp(html: str) -> datetime | None:
    match = TIMESTAMP_PATTERN.search(html)
    if not match:
        return None
    hour, minute, day, month, year = (int(g) for g in match.groups())
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _parse_price(raw: str) -> float:
    return float(raw.replace(",", "")) * VND_LUONG_PER_NGHIN_CHI


class DojiScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "doji"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT}, timeout=10.0
            ) as client:
                logger.debug("→ Doji %s", URL)
                response = await client.get(URL)
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("DOJI scraper HTTP error: %s", exc)
            return []

        html = response.text
        soup = BeautifulSoup(html, "lxml")
        timestamp = _parse_timestamp(html) or datetime.now(timezone.utc)

        table = soup.select_one(".ant-home-price table.goldprice-view")
        if not table:
            logger.warning("DOJI: price table not found in HTML")
            return []

        rows = table.select("tbody tr")
        prices: list[FetchedPrice] = []

        for row in rows:
            title_el = row.select_one("td.first span.title")
            if not title_el:
                continue
            name = title_el.get_text(strip=True)

            buy_el = row.select_one("td.goldprice-td-0 .item-relative")
            sell_el = row.select_one("td.goldprice-td-1 .item-relative")
            if not buy_el or not sell_el:
                continue

            try:
                buy_raw = buy_el.get_text(strip=True)
                sell_raw = sell_el.get_text(strip=True)
                buy = _parse_price(buy_raw)
                sell = _parse_price(sell_raw)
            except (ValueError, AttributeError):
                logger.warning("DOJI: failed to parse prices for row '%s'", name)
                continue

            if SJC_PATTERN.search(name):
                product_type = "sjc_bar"
            elif RING_GOLD_PATTERN.search(name):
                product_type = "ring_gold"
            else:
                continue

            prices.append(
                FetchedPrice(
                    source="doji",
                    product_type=product_type,
                    buy_price=buy,
                    sell_price=sell,
                    price_vnd=buy,
                    currency="VND",
                    timestamp=timestamp,
                )
            )

        return prices
