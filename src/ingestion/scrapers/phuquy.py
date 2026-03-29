"""Phú Quý gold price scraper — static HTML via httpx + BeautifulSoup."""

import html as html_mod
import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

URL = "https://phuquygroup.vn"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VND_LUONG_PER_VND_CHI = 10

SJC_PATTERN = re.compile(r"Vàng miếng SJC", re.IGNORECASE)
RING_GOLD_PATTERN = re.compile(
    r"(?:Nhẫn tròn Phú Quý 999\.9|Vàng 999\.9 phi SJC|Vàng 999\.0\s+phi SJC)",
    re.IGNORECASE,
)
TIMESTAMP_PATTERN = re.compile(
    r"cập nhật lần cuối lúc\s+(\d{1,2}):(\d{2})\s+(\d{1,2})/(\d{1,2})/(\d{4})"
)


def _parse_timestamp(raw_html: str) -> datetime | None:
    text = html_mod.unescape(raw_html)
    match = TIMESTAMP_PATTERN.search(text)
    if not match:
        return None
    hour, minute, day, month, year = (int(g) for g in match.groups())
    return datetime(year, month, day, hour, minute, tzinfo=timezone.utc)


def _parse_price(raw: str) -> float:
    return float(raw.replace(",", "").replace(".", "")) * VND_LUONG_PER_VND_CHI


class PhuQuyScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "phuquy"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT}, timeout=10.0
            ) as client:
                logger.debug("→ Phú Quý %s", URL)
                response = await client.get(URL)
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Phú Quý scraper HTTP error: %s", exc)
            return []

        html = response.text
        soup = BeautifulSoup(html, "lxml")
        timestamp = _parse_timestamp(html) or datetime.now(timezone.utc)

        table = soup.select_one("#priceList table")
        if not table:
            logger.warning("Phú Quý: price table not found in HTML")
            return []

        rows = table.select("tbody tr")
        prices: list[FetchedPrice] = []

        for row in rows:
            cells = row.select("td")
            if len(cells) < 3:
                continue

            name = cells[0].get_text(strip=True)

            buy_el = row.select_one("td.buy-price")
            sell_el = row.select_one("td.sell-price")
            if not buy_el or not sell_el:
                continue

            try:
                buy_raw = buy_el.get_text(strip=True)
                sell_raw = sell_el.get_text(strip=True)
                if not buy_raw or not sell_raw:
                    continue
                buy = _parse_price(buy_raw)
                sell = _parse_price(sell_raw)
            except (ValueError, AttributeError):
                logger.warning("Phú Quý: failed to parse prices for row '%s'", name)
                continue

            if SJC_PATTERN.search(name):
                product_type = "sjc_bar"
            elif RING_GOLD_PATTERN.search(name):
                product_type = "ring_gold"
            else:
                continue

            prices.append(
                FetchedPrice(
                    source="phuquy",
                    product_type=product_type,
                    buy_price=buy,
                    sell_price=sell,
                    price_vnd=buy,
                    currency="VND",
                    timestamp=timestamp,
                )
            )

        return prices
