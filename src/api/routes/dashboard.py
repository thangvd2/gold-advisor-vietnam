import asyncio
from collections import defaultdict

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from src.config import Settings
from src.engine.pipeline import compute_signal
from src.engine.types import SignalMode
from src.storage.database import async_session
from src.storage.repository import get_latest_prices

from pathlib import Path

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


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


@router.get("/partials/signal")
async def get_signal_partial(
    request: Request,
    mode: str = Query("saver", pattern="^(saver|trader)$"),
):
    try:
        signal_mode = SignalMode(mode.upper())
        signal = await asyncio.to_thread(compute_signal, _get_db_path(), signal_mode)

        gap = None
        if signal.gap_vnd is not None:
            from src.analysis.gap import calculate_current_gap

            gap_result = await asyncio.to_thread(calculate_current_gap, _get_db_path())
            gap = gap_result

        return templates.TemplateResponse(
            request,
            "partials/signal_card.html",
            context={"signal": signal, "gap": gap},
        )
    except Exception:
        return HTMLResponse(
            content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">Signal unavailable</p></div>',
            status_code=200,
        )


@router.get("/partials/prices")
async def get_prices_partial(request: Request):
    try:
        async with async_session() as session:
            prices = await get_latest_prices(session)

        if not prices:
            return templates.TemplateResponse(
                request,
                "partials/price_table.html",
                context={"dealers": []},
            )

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

        return templates.TemplateResponse(
            request,
            "partials/price_table.html",
            context={"dealers": dealers},
        )
    except Exception:
        return HTMLResponse(
            content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">No price data available</p></div>',
            status_code=200,
        )


@router.get("/partials/gap")
async def get_gap_partial(request: Request):
    try:
        from src.analysis.gap import calculate_current_gap

        gap = await asyncio.to_thread(calculate_current_gap, _get_db_path())
        return templates.TemplateResponse(
            request,
            "partials/gap_display.html",
            context={"gap": gap},
        )
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/gap_display.html",
            context={"gap": None},
        )


@router.get("/partials/price-chart")
async def get_price_chart_partial(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/price_chart.html",
        context={},
    )


@router.get("/partials/gap-chart")
async def get_gap_chart_partial(request: Request):
    return templates.TemplateResponse(
        request,
        "partials/gap_chart.html",
        context={},
    )


@router.get("/macro")
async def get_macro_data():
    db_path = _get_db_path()
    try:
        from src.analysis.macro import calculate_fx_trend, calculate_gold_trend

        fx_trend = await asyncio.to_thread(calculate_fx_trend, db_path)
        gold_trend = await asyncio.to_thread(calculate_gold_trend, db_path)

        dxy_value = None
        async with async_session() as session:
            from sqlalchemy import select
            from src.storage.models import PriceRecord

            stmt = (
                select(PriceRecord)
                .where(PriceRecord.product_type == "dxy")
                .order_by(PriceRecord.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record and record.price_usd:
                dxy_value = record.price_usd

        return {
            "fx_trend": fx_trend,
            "gold_trend": gold_trend,
            "dxy": dxy_value,
        }
    except Exception:
        return {"fx_trend": None, "gold_trend": None, "dxy": None}


@router.get("/partials/macro")
async def get_macro_partial(request: Request):
    try:
        db_path = _get_db_path()
        from src.analysis.macro import calculate_fx_trend, calculate_gold_trend

        fx_trend = await asyncio.to_thread(calculate_fx_trend, db_path)
        gold_trend = await asyncio.to_thread(calculate_gold_trend, db_path)

        dxy_value = None
        async with async_session() as session:
            from sqlalchemy import select
            from src.storage.models import PriceRecord

            stmt = (
                select(PriceRecord)
                .where(PriceRecord.product_type == "dxy")
                .order_by(PriceRecord.timestamp.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()
            if record and record.price_usd:
                dxy_value = record.price_usd

        return templates.TemplateResponse(
            request,
            "partials/macro_card.html",
            context={
                "fx_trend": fx_trend,
                "gold_trend": gold_trend,
                "dxy": dxy_value,
            },
        )
    except Exception:
        return templates.TemplateResponse(
            request,
            "partials/macro_card.html",
            context={"fx_trend": None, "gold_trend": None, "dxy": None},
        )
