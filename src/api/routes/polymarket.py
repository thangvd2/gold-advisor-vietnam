import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import VNTZ
from src.storage.database import async_session
from src.storage.repository import get_latest_fedwatch, get_polymarket_events

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
            events = await get_polymarket_events(session, limit=10)
            flagged = await get_polymarket_events(session, flagged_only=True, limit=5)
        context = {"events": events, "flagged": flagged}
        if events and events[0].fetched_at:
            context["fetched_at"] = events[0].fetched_at
        return templates.TemplateResponse(
            request,
            "partials/polymarket.html",
            context={"events": events, "flagged": flagged},
        )
    except Exception:
        logger.warning("Polymarket partial failed", exc_info=True)
    return HTMLResponse(
        content='<div class="card-glow rounded-2xl bg-charcoal-700/60 border border-gold-500/15 p-8 text-center"><p class="text-charcoal-400 text-sm">Polymarket data unavailable</p></div>',
        status_code=200,
    )
