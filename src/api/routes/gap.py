import asyncio

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from src.analysis.gap import calculate_current_gap, calculate_historical_gaps
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


@router.get("/current")
async def get_current_gap():
    db_path = _get_db_path()
    result = await asyncio.to_thread(calculate_current_gap, db_path)

    if result is None:
        return JSONResponse(status_code=503, content={"error": "insufficient data"})

    return {"gap": result}


@router.get("/history")
async def get_gap_history(
    range: str = Query("1W", pattern="^(1W|1M|3M|1Y)$"),
):
    db_path = _get_db_path()
    gaps = await asyncio.to_thread(calculate_historical_gaps, db_path, range)
    return {"range": range, "gaps": gaps}
