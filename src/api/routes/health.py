from fastapi import APIRouter
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import async_session

router = APIRouter()


@router.get("/health")
async def health_check():
    try:
        async with async_session() as session:
            await session.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "error"

    return {
        "status": "ok",
        "app": "gold_advisor",
        "database": db_status,
        "scheduler": "not_started",
    }
