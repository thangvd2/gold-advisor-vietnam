"""Vietcombank market rate fetcher with yfinance fallback."""

import logging
from datetime import datetime, timezone

import httpx

from src.ingestion.fetchers.fx_rate import FxRateFetcher
from src.ingestion.fetchers.base import retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

PRIMARY_URL = "https://www.vietcombank.com.vn/api/exrates/usd"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def _fetch_yfinance_fallback() -> float | None:
    import yfinance as yf

    logger.debug("→ yfinance USDVND=X (fallback)")
    ticker = yf.Ticker("USDVND=X")
    price = ticker.fast_info.last_price
    return price if price and price > 0 else None


class VietcombankFxRateFetcher(FxRateFetcher):
    @retry(max_retries=3, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        selling_rate = None

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                logger.debug("→ Vietcombank %s", PRIMARY_URL)
                response = await client.get(
                    PRIMARY_URL,
                    headers={"User-Agent": USER_AGENT},
                )
                if response.status_code == 200:
                    data = response.json()
                    selling_rate = data.get("sellingRate") or data.get("sellRate")
        except Exception as exc:
            logger.warning("Vietcombank API failed: %s", exc)

        if not selling_rate:
            selling_rate = _fetch_yfinance_fallback()
            if selling_rate:
                logger.info("Using yfinance USDVND=X fallback: %.2f", selling_rate)

        if not selling_rate or float(selling_rate) <= 0:
            logger.warning("No valid USD/VND rate from any source")
            return []

        now = datetime.now(timezone.utc)
        return [
            FetchedPrice(
                source="vietcombank",
                product_type="usd_vnd",
                sell_price=float(selling_rate),
                currency="VND",
                timestamp=now,
            )
        ]
