from fastapi import APIRouter
from sqlalchemy import text

from src.storage.database import async_session

router = APIRouter()

_app_state: dict = {}


def set_app_state(state: dict) -> None:
    _app_state.update(state)


@router.get("/health")
async def health_check():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    scheduler_info = _app_state.get("scheduler")
    if scheduler_info and scheduler_info.running:
        scheduler_status = "running"
        next_fire = scheduler_info.get_jobs()
        next_fire_time = (
            (next_fire[0].next_run_time.isoformat() if next_fire else None)
            if next_fire
            else None
        )
    else:
        scheduler_status = "not_started"
        next_fire_time = None

    return {
        "status": "ok",
        "app": "gold_advisor",
        "database": db_status,
        "scheduler": scheduler_status,
        "next_fire_time": next_fire_time,
    }
