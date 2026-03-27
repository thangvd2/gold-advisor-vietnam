import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf

from src.ingestion.fetchers.base import retry

logger = logging.getLogger(__name__)


class FedWatchFetcher:
    @retry(max_retries=2)
    async def fetch(self) -> dict | None:
        return await self._fetch_fed_funds()

    async def _fetch_fed_funds(self) -> dict | None:
        try:
            result = await asyncio.to_thread(self._get_zq_price)
            return result
        except Exception:
            logger.warning("Error fetching ZQ=F futures", exc_info=True)
            return None

    def _get_zq_price(self) -> dict | None:
        ticker = yf.Ticker("ZQ=F")
        hist = ticker.history(period="5d")
        if hist.empty:
            logger.warning("No data from ZQ=F ticker")
            return None
        close_price = hist["Close"].iloc[-1]
        if close_price is None:
            return None
        implied_rate = 100 - float(close_price)
        now = datetime.now(timezone.utc)
        return {
            "implied_rate": implied_rate,
            "futures_price": float(close_price),
            "contract": "ZQ=F",
        }
