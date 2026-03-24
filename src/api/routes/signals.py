import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.config import Settings
from src.engine.pipeline import compute_signal
from src.engine.types import SignalMode
from src.storage.database import async_session
from src.storage.repository import get_signals_since

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


@router.get("/current")
async def get_current_signal(mode: str = Query("saver", pattern="^(saver|trader)$")):
    signal_mode = SignalMode(mode.upper())
    signal = await asyncio.to_thread(compute_signal, _get_db_path(), signal_mode)

    if signal.confidence == 0 and signal.recommendation == "HOLD":
        return JSONResponse(
            status_code=503,
            content={"error": "insufficient data for signal computation"},
        )

    return signal.__dict__


@router.get("/history")
async def get_signal_history(
    mode: str | None = Query(None, pattern="^(saver|trader)$"),
    days: int = Query(7, ge=1, le=90),
):
    since_dt = datetime.now(timezone.utc) - timedelta(days=days)
    signal_mode = SignalMode(mode.upper()) if mode else None

    async with async_session() as session:
        records = await get_signals_since(session, since_dt, mode=signal_mode)

    signals = []
    for rec in records:
        signals.append(
            {
                "id": rec.id,
                "recommendation": rec.recommendation,
                "confidence": rec.confidence,
                "gap_vnd": rec.gap_vnd,
                "gap_pct": rec.gap_pct,
                "mode": rec.mode,
                "reasoning": rec.reasoning,
                "created_at": rec.created_at.isoformat() if rec.created_at else None,
            }
        )

    return {"signals": signals}
