"""yfinance-based XAUUSD price fetcher."""

import asyncio
import logging
from datetime import datetime, timezone

import yfinance as yf

from src.ingestion.fetchers.base import DataSource, retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

PRIMARY_TICKER = "GC=F"
FALLBACK_TICKER = "XAUUSD=X"


class YFinanceGoldFetcher(DataSource):
    @retry(max_retries=3, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        return await self._fetch_from_tickers()

    async def _fetch_from_tickers(self) -> list[FetchedPrice]:
        for ticker_symbol in [PRIMARY_TICKER, FALLBACK_TICKER]:
            try:
                result = await asyncio.to_thread(self._get_price, ticker_symbol)
                if result:
                    return result
                logger.warning("No data from ticker %s, trying next", ticker_symbol)
            except Exception:
                logger.warning(
                    "Error fetching %s, trying next ticker",
                    ticker_symbol,
                    exc_info=True,
                )
        return []

    def _get_price(self, ticker_symbol: str) -> list[FetchedPrice]:
        ticker = yf.Ticker(ticker_symbol)
        fast_info = ticker.fast_info
        price = fast_info.last_price
        if price is None:
            return []
        now = datetime.now(timezone.utc)
        return [
            FetchedPrice(
                source="yfinance",
                product_type="xau_usd",
                buy_price=float(price),
                sell_price=float(fast_info.previous_close or price),
                price_usd=float(price),
                currency="USD",
                timestamp=now,
            )
        ]
