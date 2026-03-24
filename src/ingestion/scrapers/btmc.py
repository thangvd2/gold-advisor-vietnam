import logging
import re
from datetime import datetime, timezone

import httpx
from bs4 import BeautifulSoup

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

API_URL = "https://api.btmc.vn/api/BTMCAPI/getpricebtmc"
HTML_URL = "https://btmc.vn/Home/BGiaVang"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
VND_LUONG_PER_NGHIN_CHI = 10_000

SJC_BAR_KEYWORDS = ["VÀNG MIẾNG SJC", "VANG MIENG SJC"]
RING_GOLD_KEYWORDS = ["NHẪN TRÒN", "NHAN TRON", "NHẪN TRƠN"]
BTMC_BAR_KEYWORDS = ["VÀNG MIẾNG VRTL", "VANG MIENG VRTL"]

JSON_SJC_BAR_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in ["VANG_MIENG_SJC", "sjc"]
]
JSON_RING_PATTERNS = [re.compile(p, re.IGNORECASE) for p in ["NHAN_TRON", "ring"]]
JSON_BTMC_BAR_PATTERNS = [
    re.compile(p, re.IGNORECASE) for p in ["VANG_MIENG_VRTL", "vrtl"]
]


def _parse_json_price(raw: str) -> float | None:
    try:
        val = float(raw.replace(",", ""))
        return val * VND_LUONG_PER_NGHIN_CHI
    except (ValueError, TypeError):
        return None


def _classify_json_type(type_str: str) -> str | None:
    for pat in JSON_SJC_BAR_PATTERNS:
        if pat.search(type_str):
            return "sjc_bar"
    for pat in JSON_BTMC_BAR_PATTERNS:
        if pat.search(type_str):
            return "sjc_bar"
    for pat in JSON_RING_PATTERNS:
        if pat.search(type_str):
            return "ring_gold"
    return None


def _parse_html(html: str) -> list[FetchedPrice]:
    soup = BeautifulSoup(html, "lxml")
    rows = soup.select("table.bd_price_home tr")
    if not rows:
        rows = soup.select("table tr")

    seen_types: set[str] = set()
    prices: list[FetchedPrice] = []

    for row in rows:
        cells = row.find_all("td")
        if len(cells) < 5:
            continue

        brand = cells[0].get_text(strip=True).upper()
        gold_type = cells[1].get_text(strip=True).upper()

        buy_raw = cells[3].get_text(strip=True)
        sell_raw = cells[4].get_text(strip=True)

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
        prices = await self._try_json_api()
        if prices:
            return prices

        return await self._try_html_fallback()

    async def _try_json_api(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            ) as client:
                response = await client.get(API_URL)
                response.raise_for_status()
        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.ConnectError,
        ) as exc:
            logger.warning("BTMC JSON API unreachable: %s", exc)
            return []

        try:
            body = response.json()
        except Exception as exc:
            logger.warning("BTMC JSON parse error: %s", exc)
            return []

        if not isinstance(body, list):
            logger.warning("BTMC: unexpected JSON root type (expected list)")
            return []

        seen_types: set[str] = set()
        prices: list[FetchedPrice] = []

        for item in body:
            if not isinstance(item, dict):
                continue

            type_str = item.get("type", item.get("Type", item.get("name", "")))
            product_type = _classify_json_type(str(type_str))
            if product_type is None:
                continue
            if product_type in seen_types:
                continue
            seen_types.add(product_type)

            buy_raw = item.get("buy", item.get("Buy", item.get("buyPrice", "")))
            sell_raw = item.get("sell", item.get("Sell", item.get("sellPrice", "")))

            buy = _parse_json_price(str(buy_raw))
            sell = _parse_json_price(str(sell_raw))

            if buy is None or sell is None:
                continue

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

    async def _try_html_fallback(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(
                headers={"User-Agent": USER_AGENT},
                timeout=10.0,
            ) as client:
                response = await client.get(HTML_URL)
                response.raise_for_status()
        except (
            httpx.TimeoutException,
            httpx.HTTPStatusError,
            httpx.ConnectError,
        ) as exc:
            logger.error("BTMC HTML fallback also failed: %s", exc)
            return []

        return _parse_html(response.text)
