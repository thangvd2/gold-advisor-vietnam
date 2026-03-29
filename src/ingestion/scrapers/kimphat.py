"""Kim Phát jewelry gold price scraper — HTML via httpx GET + BeautifulSoup.

URL: https://kimphat.evosoft.vn/
Parses static HTML table for "NHẪN TRÒN 99.99" (ring gold) prices only.
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

URL = "https://kimphat.evosoft.vn/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
CHI_PER_LUONG = 10
RING_GOLD_PATTERN = "NHẪN TRÒN 99.99"


def _parse_price(text: str) -> float | None:
    try:
        return float(text.replace(",", "").strip())
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
        hour, minute = (int(p) for p in time_part.split(":"))
        vn_dt = datetime(year, month, day, hour, minute, tzinfo=VNTZ)
        return vn_dt.astimezone(timezone.utc)
    except (ValueError, IndexError, AttributeError):
        return None


class KimPhatScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "kimphat"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            ) as client:
                logger.debug("→ Kim Phát %s", URL)
                response = await client.get(URL)
                response.raise_for_status()
        except (httpx.TimeoutException, httpx.HTTPStatusError) as exc:
            logger.error("Kim Phát scraper HTTP error: %s", exc)
            return []

        try:
            soup = BeautifulSoup(response.text, "lxml")
        except Exception as exc:
            logger.error("Kim Phát scraper HTML parse error: %s", exc)
            return []

        tbody = soup.find("tbody")
        if not tbody:
            logger.warning("Kim Phát: no <tbody> found")
            return []

        for row in tbody.find_all("tr"):
            th = row.find("th", class_="column-type")
            if not th:
                continue

            name_div = th.find("div")
            if not name_div:
                continue

            product_name = name_div.get_text(separator=" ", strip=True)
            if RING_GOLD_PATTERN not in product_name:
                continue

            price_cells = row.find_all("td", class_="column-price")
            if len(price_cells) < 2:
                logger.warning("Kim Phát: insufficient price cells for ring gold")
                continue

            buy_text = price_cells[0].find("div", class_="price")
            sell_text = price_cells[1].find("div", class_="price")

            if not buy_text or not sell_text:
                logger.warning("Kim Phát: price div not found")
                continue

            buy_per_chi = _parse_price(buy_text.get_text())
            sell_per_chi = _parse_price(sell_text.get_text())

            if buy_per_chi is None or sell_per_chi is None:
                logger.warning("Kim Phát: failed to parse prices")
                continue

            buy_per_luong = buy_per_chi * CHI_PER_LUONG
            sell_per_luong = sell_per_chi * CHI_PER_LUONG

            time_div = th.find("div", class_="time")
            timestamp = None
            if time_div:
                timestamp = _parse_timestamp(time_div.get_text())
            if timestamp is None:
                timestamp = datetime.now(timezone.utc)

            return [
                FetchedPrice(
                    source="kimphat",
                    product_type="ring_gold",
                    buy_price=buy_per_luong,
                    sell_price=sell_per_luong,
                    price_vnd=buy_per_luong,
                    currency="VND",
                    timestamp=timestamp,
                )
            ]

        logger.warning("Kim Phát: 'NHẪN TRÒN 99.99' row not found")
        return []
