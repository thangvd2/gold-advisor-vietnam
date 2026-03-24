"""Vietcombank market rate fetcher."""

import logging
from datetime import datetime, timezone

import httpx

from src.ingestion.fetchers.fx_rate import FxRateFetcher
from src.ingestion.fetchers.base import retry
from src.ingestion.models import FetchedPrice

logger = logging.getLogger(__name__)

VCB_API_URL = "https://www.vietcombank.com.vn/api/exrates/usd"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


class VietcombankFxRateFetcher(FxRateFetcher):
    @retry(max_retries=3, backoff_factor=1.0)
    async def fetch(self) -> list[FetchedPrice]:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    VCB_API_URL,
                    headers={"User-Agent": USER_AGENT},
                )
                if response.status_code != 200:
                    logger.warning(
                        "Vietcombank API returned status %d", response.status_code
                    )
                    return []

                data = response.json()
                selling_rate = data.get("sellingRate") or data.get("sellRate")
                if not selling_rate or float(selling_rate) <= 0:
                    logger.warning("Vietcombank API returned invalid rate: %s", data)
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
        except Exception:
            logger.warning("Failed to fetch Vietcombank FX rate", exc_info=True)
            return []
