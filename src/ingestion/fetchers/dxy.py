import logging
from datetime import datetime, timezone

import yfinance as yf

from src.ingestion.fetchers.base import DataSource
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

DXY_TICKER = "^DXY"


class DXYFetcher(DataSource):
    async def fetch(self) -> list[FetchedPrice]:
        try:
            ticker = yf.Ticker(DXY_TICKER)
            price = ticker.fast_info.last_price

            if price is None or price <= 0:
                return []

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
            logger.warning("Failed to fetch DXY index", exc_info=True)
            return []
