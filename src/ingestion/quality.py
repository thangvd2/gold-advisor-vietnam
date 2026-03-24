"""Data quality checks for gold price data."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.models import DataQualityAlert, PriceRecord
from src.storage.repository import save_quality_alert

logger = logging.getLogger(__name__)


def _ensure_aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


async def check_freshness(
    session: AsyncSession,
    source: str,
    product_type: str,
    threshold_minutes: int,
) -> DataQualityAlert | None:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)
    stmt = (
        select(PriceRecord)
        .where(PriceRecord.source == source)
        .where(PriceRecord.product_type == product_type)
        .order_by(PriceRecord.fetched_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    latest = result.scalar_one_or_none()

    if latest is None:
        return None

    if _ensure_aware(latest.fetched_at) < cutoff:
        minutes_stale = (cutoff - _ensure_aware(latest.fetched_at)).total_seconds() / 60
        return await save_quality_alert(
            session,
            check_type="freshness",
            severity="warning",
            source=source,
            message=f"Data stale: last fetched {minutes_stale:.0f} minutes ago (threshold: {threshold_minutes} min)",
        )

    return None


async def check_anomaly(
    session: AsyncSession,
    new_record: PriceRecord,
    threshold_percent: float,
) -> DataQualityAlert | None:
    stmt = (
        select(PriceRecord)
        .where(PriceRecord.source == new_record.source)
        .where(PriceRecord.product_type == new_record.product_type)
        .where(PriceRecord.id != new_record.id)
        .order_by(PriceRecord.timestamp.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    previous = result.scalar_one_or_none()

    if previous is None:
        return None

    ref_price_usd = (
        new_record.price_usd if new_record.price_usd else new_record.price_vnd
    )
    prev_price_usd = previous.price_usd if previous.price_usd else previous.price_vnd

    if ref_price_usd is None or prev_price_usd is None or prev_price_usd == 0:
        return None

    pct_change = abs(ref_price_usd - prev_price_usd) / prev_price_usd * 100
    if pct_change > threshold_percent:
        return await save_quality_alert(
            session,
            check_type="anomaly",
            severity="warning",
            source=new_record.source,
            message=f"Price jumped {pct_change:.1f}% (threshold: {threshold_percent}%)",
        )

    return None


async def check_missing(
    session: AsyncSession,
    source: str,
    product_type: str,
) -> DataQualityAlert:
    return await save_quality_alert(
        session,
        check_type="missing",
        severity="critical",
        source=source,
        message=f"No data received for {source}/{product_type}",
    )


async def run_quality_checks(
    session: AsyncSession,
    source: str,
    product_type: str,
    threshold_minutes: int,
) -> list[DataQualityAlert]:
    alerts = []
    alert = await check_freshness(session, source, product_type, threshold_minutes)
    if alert:
        alerts.append(alert)
    return alerts
