import logging
from datetime import datetime, timezone

import yfinance as yf

from src.ingestion.fetchers.base import DataSource
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

# Suppress yfinance's noisy "possibly delisted" warnings for known-broken tickers
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

DXY_TICKER = "^DXY"
DXY_FALLBACK = "DX-Y.NYB"


class DXYFetcher(DataSource):
    async def fetch(self) -> list[FetchedPrice]:
        for ticker_symbol in [DXY_TICKER, DXY_FALLBACK]:
            try:
                logger.debug("→ yfinance %s", ticker_symbol)
                ticker = yf.Ticker(ticker_symbol)
                price = ticker.fast_info.last_price

                if price is None or price <= 0:
                    continue

                now = datetime.now(timezone.utc)
                return [
                    FetchedPrice(
                        source="yfinance",
                        product_type="dxy",
                        price_usd=price,
                        currency="USD",
                        timestamp=now,
                    )
                ]
            except Exception:
                logger.warning(
                    "Failed to fetch DXY from %s", ticker_symbol, exc_info=True
                )
        return []
