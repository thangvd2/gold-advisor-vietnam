import asyncio

from fastapi import APIRouter, Query

from src.analysis.prices import get_price_series
from src.config import Settings

router = APIRouter()


def get_settings() -> Settings:
    return Settings()


def _get_db_path() -> str:
    settings = get_settings()
    url = settings.database_url
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return url[len(prefix) :]
    return url


@router.get("/history")
async def get_price_history(
    product_type: str = Query(..., pattern="^(sjc_bar|ring_gold|xau_usd)$"),
    range: str = Query("1M", pattern="^(1D|1W|1M|1Y)$"),
):
    db_path = _get_db_path()
    prices = await asyncio.to_thread(get_price_series, db_path, product_type, range)
    return {"product_type": product_type, "range": range, "prices": prices}
