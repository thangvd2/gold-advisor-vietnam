"""Kim Khánh Việt Hùng gold price scraper — HTML via httpx GET + BeautifulSoup.

URL: https://kimkhanhviethung.vn/tra-cuu-gia-vang.html
Parses static HTML table for "Vàng 999.9" (ring gold) prices only.
Prices are per chỉ (~3.75g); multiply by 10 to get per lượng (37.5g).
"""

import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.config import VNTZ
from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

URL = "https://kimkhanhviethung.vn/tra-cuu-gia-vang.html"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
CHI_PER_LUONG = 10
RING_GOLD_PATTERN = "999.9"


def _parse_price(text: str) -> float | None:
    try:
        return float(text.replace(".", "").replace("đ", "").strip())
    except (ValueError, AttributeError):
        return None


def _parse_timestamp(text: str) -> datetime | None:
    try:
        parts = text.strip().split()
        if len(parts) < 2:
            return None
        date_part = parts[0]
        time_part = parts[1]
        day, month, year = (int(p) for p in date_part.split("/"))
        hour, minute, second = (int(p) for p in time_part.split(":"))
        vn_dt = datetime(year, month, day, hour, minute, second, tzinfo=VNTZ)
        return vn_dt.astimezone(timezone.utc)
    except (ValueError, IndexError, AttributeError):
        return None


async def _fetch_page() -> tuple[float, float, datetime] | None:
    try:
        async with httpx.AsyncClient(
            headers={"User-Agent": USER_AGENT},
            timeout=10.0,
        ) as client:
            logger.debug("→ KKVH %s", URL)
            response = await client.get(URL)
            response.raise_for_status()
    except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
        logger.error("KKVH scraper HTTP error: %s", exc)
        return None

    try:
        soup = BeautifulSoup(response.text, "lxml")
    except Exception as exc:
        logger.error("KKVH scraper HTML parse error: %s", exc)
        return None

    timestamp = None
    timestamp_div = soup.find("div", class_="sub_tieude_gc")
    if timestamp_div:
        b_tag = timestamp_div.find("b")
        if b_tag:
            timestamp_text = b_tag.get_text(strip=True)
            if "Ngày cập nhật:" in timestamp_text:
                timestamp_text = timestamp_text.replace("Ngày cập nhật:", "").strip()
            timestamp = _parse_timestamp(timestamp_text)
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    table = soup.find("table", class_="table")
    if not table:
        logger.warning("KKVH: no <table class='table'> found")
        return None

    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) < 3:
            continue

        name_cell = cells[0]
        product_name = name_cell.get_text(separator=" ", strip=True)
        if RING_GOLD_PATTERN not in product_name:
            continue

        buy_text = cells[1].get_text(strip=True)
        sell_text = cells[2].get_text(strip=True)

        buy_per_chi = _parse_price(buy_text)
        sell_per_chi = _parse_price(sell_text)

        if buy_per_chi is None or sell_per_chi is None:
            logger.warning("KKVH: failed to parse prices")
            continue

        buy_per_luong = buy_per_chi * CHI_PER_LUONG
        sell_per_luong = sell_per_chi * CHI_PER_LUONG

        return (buy_per_luong, sell_per_luong, timestamp)

    logger.warning("KKVH: 'Vàng 999.9' row not found")
    return None


class KimKhanhDealerScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "kimkhanh"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        result = await _fetch_page()
        if result is None:
            return []
        buy_per_luong, sell_per_luong, timestamp = result
        return [
            FetchedPrice(
                source="kimkhanh",
                product_type="ring_gold",
                buy_price=buy_per_luong,
                sell_price=sell_per_luong,
                price_vnd=buy_per_luong,
                currency="VND",
                timestamp=timestamp,
            )
        ]


class KimKhanhLocalScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "local"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        result = await _fetch_page()
        if result is None:
            return []
        buy_per_luong, sell_per_luong, timestamp = result
        return [
            FetchedPrice(
                source="local",
                product_type="ring_gold",
                buy_price=buy_per_luong,
                sell_price=sell_per_luong,
                price_vnd=buy_per_luong,
                currency="VND",
                timestamp=timestamp,
            )
        ]
