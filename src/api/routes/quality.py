"""Quality monitoring API endpoints."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from src.storage.database import async_session
from src.storage.repository import get_latest_prices, get_recent_alerts

router = APIRouter()


@router.get("/alerts")
async def get_alerts(
    hours: int = Query(default=24, ge=1, le=168),
):
    capped_hours = min(max(hours, 1), 168)

    async with async_session() as session:
        alerts = await get_recent_alerts(session, hours=capped_hours)

    return {
        "alerts": [
            {
                "check_type": a.check_type,
                "severity": a.severity,
                "source": a.source,
                "message": a.message,
                "detected_at": a.detected_at.isoformat() if a.detected_at else None,
            }
            for a in alerts
        ]
    }


@router.get("/status")
async def get_quality_status():
    from src.config import Settings

    settings = Settings()
    threshold_minutes = settings.freshness_threshold_minutes
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

    async with async_session() as session:
        latest_records = await get_latest_prices(session)

    sources = []
    for record in latest_records:
        fetched_at = record.fetched_at
        if fetched_at.tzinfo is None:
            fetched_at = fetched_at.replace(tzinfo=timezone.utc)

        sources.append(
            {
                "source": record.source,
                "product_type": record.product_type,
                "latest_price": record.price_usd or record.price_vnd,
                "price_usd": record.price_usd,
                "price_vnd": record.price_vnd,
                "fetched_at": fetched_at.isoformat(),
                "validation_status": record.validation_status,
                "is_stale": fetched_at < cutoff,
            }
        )

    return {"sources": sources}
