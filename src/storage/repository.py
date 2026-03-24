"""CRUD operations for price_history, data_quality_alerts, and signal_history tables."""

import json
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ingestion.models import FetchedPrice
from src.storage.models import DataQualityAlert, PriceRecord, SignalRecord


async def save_price(
    session: AsyncSession,
    fetched: FetchedPrice,
    validation_status: str = "valid",
) -> PriceRecord:
    record = PriceRecord(
        source=fetched.source,
        product_type=fetched.product_type,
        buy_price=fetched.buy_price,
        sell_price=fetched.sell_price,
        price_usd=fetched.price_usd,
        price_vnd=fetched.price_vnd,
        currency=fetched.currency,
        timestamp=fetched.timestamp,
        fetched_at=fetched.fetched_at,
        validation_status=validation_status,
    )
    if record.buy_price is not None and record.sell_price is not None:
        record.spread = record.sell_price - record.buy_price
    session.add(record)
    await session.flush()
    return record


async def get_latest_prices(
    session: AsyncSession,
    source: str | None = None,
    product_type: str | None = None,
) -> list[PriceRecord]:
    latest_subq = select(
        PriceRecord.source,
        PriceRecord.product_type,
        func.max(PriceRecord.timestamp).label("max_ts"),
    ).group_by(PriceRecord.source, PriceRecord.product_type)
    if source:
        latest_subq = latest_subq.where(PriceRecord.source == source)
    if product_type:
        latest_subq = latest_subq.where(PriceRecord.product_type == product_type)

    latest_subq = latest_subq.subquery()

    stmt = select(PriceRecord).join(
        latest_subq,
        (PriceRecord.source == latest_subq.c.source)
        & (PriceRecord.product_type == latest_subq.c.product_type)
        & (PriceRecord.timestamp == latest_subq.c.max_ts),
    )
    if source:
        stmt = stmt.where(PriceRecord.source == source)
    if product_type:
        stmt = stmt.where(PriceRecord.product_type == product_type)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_prices_since(
    session: AsyncSession,
    since_dt: datetime,
    source: str | None = None,
    product_type: str | None = None,
) -> list[PriceRecord]:
    stmt = select(PriceRecord).where(PriceRecord.timestamp >= since_dt)
    if source:
        stmt = stmt.where(PriceRecord.source == source)
    if product_type:
        stmt = stmt.where(PriceRecord.product_type == product_type)
    stmt = stmt.order_by(PriceRecord.timestamp.asc())

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def save_quality_alert(
    session: AsyncSession,
    check_type: str,
    severity: str,
    source: str,
    message: str,
) -> DataQualityAlert:
    alert = DataQualityAlert(
        check_type=check_type,
        severity=severity,
        source=source,
        message=message,
    )
    session.add(alert)
    await session.flush()
    return alert


async def get_recent_alerts(
    session: AsyncSession,
    hours: int = 24,
) -> list[DataQualityAlert]:
    from datetime import timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    stmt = (
        select(DataQualityAlert)
        .where(DataQualityAlert.detected_at >= since)
        .order_by(DataQualityAlert.detected_at.desc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def save_signal(session: AsyncSession, signal) -> SignalRecord:
    factors_json = json.dumps(
        [
            {
                "name": f.name,
                "direction": f.direction,
                "weight": f.weight,
                "confidence": f.confidence,
            }
            for f in signal.factors
        ]
    )
    record = SignalRecord(
        recommendation=signal.recommendation.value,
        confidence=signal.confidence,
        gap_vnd=signal.gap_vnd,
        gap_pct=signal.gap_pct,
        mode=signal.mode.value,
        reasoning=signal.reasoning,
        factor_data=factors_json,
    )
    session.add(record)
    await session.flush()
    return record


async def get_latest_signal(session: AsyncSession, mode=None) -> SignalRecord | None:
    stmt = select(SignalRecord).order_by(SignalRecord.created_at.desc()).limit(1)
    if mode is not None:
        stmt = stmt.where(SignalRecord.mode == mode.value)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_signals_since(
    session: AsyncSession, since_dt: datetime, mode=None
) -> list[SignalRecord]:
    stmt = select(SignalRecord).where(SignalRecord.created_at >= since_dt)
    if mode is not None:
        stmt = stmt.where(SignalRecord.mode == mode.value)
    stmt = stmt.order_by(SignalRecord.created_at.asc())
    result = await session.execute(stmt)
    return list(result.scalars().all())
