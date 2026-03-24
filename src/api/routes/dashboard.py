import asyncio
from collections import defaultdict

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.config import Settings
from src.engine.pipeline import compute_signal
from src.engine.types import SignalMode
from src.storage.database import async_session
from src.storage.repository import get_latest_prices

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


@router.get("/prices")
async def get_dashboard_prices():
    async with async_session() as session:
        prices = await get_latest_prices(session)

    if not prices:
        return {"dealers": []}

    grouped: dict[str, dict] = defaultdict(
        lambda: {"source": "", "products": [], "fetched_at": None}
    )

    for p in prices:
        entry = grouped[p.source]
        entry["source"] = p.source

        if p.product_type == "xau_usd":
            product = {
                "product_type": p.product_type,
                "price_usd": p.price_usd,
                "price_vnd": p.price_vnd,
            }
        else:
            product = {
                "product_type": p.product_type,
                "buy_price": p.buy_price,
                "sell_price": p.sell_price,
                "spread": p.spread,
            }

        entry["products"].append(product)
        if entry["fetched_at"] is None:
            entry["fetched_at"] = p.fetched_at.isoformat() if p.fetched_at else None

    dealers = list(grouped.values())
    for d in dealers:
        d["fetched_at"] = d["fetched_at"]

    return {"dealers": dealers}


@router.get("/signal")
async def get_dashboard_signal(
    mode: str = Query("saver", pattern="^(saver|trader)$"),
):
    signal_mode = SignalMode(mode.upper())
    signal = await asyncio.to_thread(compute_signal, _get_db_path(), signal_mode)

    if signal.confidence == 0 and signal.recommendation == "HOLD":
        return JSONResponse(
            status_code=503,
            content={"error": "insufficient data"},
        )

    return signal.__dict__
