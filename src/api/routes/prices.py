import asyncio
import sqlite3
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.analysis.prices import get_price_series
from src.config import Settings

router = APIRouter()


class LocalPriceInput(BaseModel):
    buy_price: float = Field(..., gt=0, description="Buy price in VND per lượng")
    sell_price: float = Field(..., gt=0, description="Sell price in VND per lượng")


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
    range: str = Query("1M", pattern="^(1D|1W|1M|3M|1Y)$"),
    source: str = Query(None, max_length=50),
    source_exclude: str = Query(None, max_length=50),
):
    db_path = _get_db_path()
    prices = await asyncio.to_thread(
        get_price_series, db_path, product_type, range, source, source_exclude
    )
    return {"product_type": product_type, "range": range, "prices": prices}


@router.post("/local")
async def update_local_price(data: LocalPriceInput):
    if data.sell_price <= data.buy_price:
        raise HTTPException(
            status_code=400, detail="sell_price must be greater than buy_price"
        )

    now = datetime.now(timezone.utc)
    db_path = _get_db_path()

    def _save():
        conn = sqlite3.connect(db_path)
        try:
            conn.execute(
                """INSERT INTO price_history
                   (source, product_type, buy_price, sell_price, spread,
                    price_vnd, currency, timestamp, fetched_at, validation_status)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    "local",
                    "ring_gold",
                    data.buy_price,
                    data.sell_price,
                    data.sell_price - data.buy_price,
                    data.buy_price,
                    "VND",
                    now,
                    now.isoformat(),
                    "valid",
                ),
            )
            conn.commit()
        finally:
            conn.close()

    await asyncio.to_thread(_save)
    return {
        "status": "ok",
        "source": "local",
        "product_type": "ring_gold",
        "buy_price": data.buy_price,
        "sell_price": data.sell_price,
        "spread": data.sell_price - data.buy_price,
    }
