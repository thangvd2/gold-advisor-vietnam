import logging
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

URL = "https://btmc.vn/Home/BGiaVang"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VND_LUONG_PER_NGHIN_CHI = 10_000

SJC_BAR_KEYWORDS = ["VÀNG MIẾNG SJC", "VANG MIENG SJC"]
RING_GOLD_KEYWORDS = ["NHẪN TRÒN", "NHAN TRON", "NHẪN TRƠN"]
BTMC_BAR_KEYWORDS = ["VÀNG MIẾNG VRTL", "VANG MIENG VRTL"]


def _extract_row(cells: list, n_cols: int) -> tuple[str, str, str, str] | None:
    if n_cols >= 5:
        brand = cells[0].get_text(strip=True).upper()
        gold_type = cells[1].get_text(strip=True).upper()
        buy_raw = cells[3].get_text(strip=True)
        sell_raw = cells[4].get_text(strip=True)
    elif n_cols >= 4:
        brand = cells[0].get_text(strip=True).upper()
        gold_type = ""
        buy_raw = cells[2].get_text(strip=True)
        sell_raw = cells[3].get_text(strip=True)
    else:
        return None
    return brand, gold_type, buy_raw, sell_raw


def _parse_html(html: str) -> list[FetchedPrice]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.bd_price_home tr")
    if not rows:
        rows = soup.select("table tr")

    seen_types: set[str] = set()
    prices: list[FetchedPrice] = []

    for row in rows:
        cells = row.find_all("td")
        extracted = _extract_row(cells, len(cells))
        if not extracted:
            continue
        brand, gold_type, buy_raw, sell_raw = extracted

        if "LIÊN HỆ" in sell_raw or not buy_raw:
            continue

        try:
            buy = float(buy_raw.replace(",", "")) * VND_LUONG_PER_NGHIN_CHI
            sell = float(sell_raw.replace(",", "")) * VND_LUONG_PER_NGHIN_CHI
        except (ValueError, TypeError):
            continue

        product_type = None
        combined = f"{brand} {gold_type}"
        for kw in SJC_BAR_KEYWORDS + BTMC_BAR_KEYWORDS:
            if kw.upper() in combined:
                product_type = "sjc_bar"
                break
        if product_type is None:
            for kw in RING_GOLD_KEYWORDS:
                if kw.upper() in combined:
                    product_type = "ring_gold"
                    break

        if product_type is None:
            continue
        if product_type in seen_types:
            continue
        seen_types.add(product_type)

        prices.append(
            FetchedPrice(
                source="btmc",
                product_type=product_type,
                buy_price=buy,
                sell_price=sell,
                price_vnd=buy,
                currency="VND",
                timestamp=datetime.now(timezone.utc),
            )
        )

    return prices


class BTMCScraper(DataSource):
    @property
    def source_name(self) -> str:
        return "btmc"

    @retry(max_retries=2, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            ) as client:
                logger.debug("→ BTMC %s", URL)
                response = await client.get(URL)
                response.raise_for_status()
        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.ConnectError,
        ) as exc:
            logger.warning("BTMC HTML page unreachable: %s", exc)
            return []

        return _parse_html(response.text)
