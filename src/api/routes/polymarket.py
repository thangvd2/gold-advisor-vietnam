import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import VNTZ
from src.storage.database import async_session
from src.storage.repository import (
    dismiss_signal,
    get_latest_fedwatch,
    get_polymarket_events,
    get_recent_smart_signals,
)

logger = logging.getLogger(__name__)

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _vn_time(value, fmt="%d/%m/%Y %H:%M"):
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value[:19] if len(value) >= 19 else value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(VNTZ).strftime(fmt)


templates.env.filters["vn_time"] = _vn_time


@router.get("/partials/fedwatch")
async def fedwatch_partial(request: Request):
    try:
        async with async_session() as session:
            snapshot = await get_latest_fedwatch(session)
        if snapshot:
            vn_dt = (
                snapshot.fetched_at.astimezone(VNTZ)
                if snapshot.fetched_at.tzinfo
                else snapshot.fetched_at.replace(tzinfo=timezone.utc).astimezone(VNTZ)
            )
        return templates.TemplateResponse(
            request,
            "partials/fedwatch.html",
            context={
                "fedwatch_data": snapshot,
            },
        )
    except Exception:
        logger.warning("FedWatch partial failed", exc_info=True)
    return HTMLResponse(
        content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">FedWatch data unavailable</p></div>',
        status_code=200,
    )


@router.get("/partials/polymarket")
async def polymarket_partial(request: Request):
    try:
        async with async_session() as session:
            gold_macro = await get_polymarket_events(
                session, event_type="gold_macro", limit=10
            )
        fetched_at = None
        if gold_macro and gold_macro[0].fetched_at:
            fetched_at = gold_macro[0].fetched_at
        return templates.TemplateResponse(
            request,
            "partials/polymarket.html",
            context={
                "gold_macro": gold_macro,
                "fetched_at": fetched_at,
            },
        )
    except Exception:
        logger.warning("Polymarket partial failed", exc_info=True)
    return HTMLResponse(
        content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">Polymarket data unavailable</p></div>',
        status_code=200,
    )


@router.get("/partials/polymarket/market-movers")
async def market_movers_partial(request: Request):
    try:
        async with async_session() as session:
            market_movers = await get_polymarket_events(
                session, event_type="market_mover", limit=20
            )
        fetched_at = None
        if market_movers and market_movers[0].fetched_at:
            fetched_at = market_movers[0].fetched_at
        return templates.TemplateResponse(
            request,
            "partials/polymarket_market_movers.html",
            context={
                "market_movers": market_movers,
                "fetched_at": fetched_at,
            },
        )
    except Exception:
        logger.warning("Market movers partial failed", exc_info=True)
    return HTMLResponse(
        content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">Market movers unavailable</p></div>',
        status_code=200,
    )


@router.get("/polymarket")
async def polymarket_page(request: Request):
    return templates.TemplateResponse(
        request,
        "polymarket.html",
        context={},
    )


@router.get("/partials/polymarket/smart-signals")
async def smart_signals_partial(request: Request):
    try:
        async with async_session() as session:
            signals = await get_recent_smart_signals(session, hours=48, limit=20)
        return templates.TemplateResponse(
            request,
            "partials/polymarket_smart_signals.html",
            context={"signals": signals},
        )
    except Exception:
        logger.warning("Smart signals partial failed", exc_info=True)
        return HTMLResponse(
            content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">Smart signals unavailable</p></div>',
            status_code=200,
        )


@router.delete("/api/smart-signals/{signal_id}/dismiss")
async def dismiss_smart_signal(signal_id: int):
    try:
        async with async_session() as session:
            await dismiss_signal(session, signal_id)
            await session.commit()
        return HTMLResponse(content="", status_code=204)
    except Exception:
        logger.warning("Dismiss signal failed", exc_info=True)
        return HTMLResponse(content="Error", status_code=500)
