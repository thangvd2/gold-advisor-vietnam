"""CRUD operations for price_history, data_quality_alerts, and signal_history tables."""

import json
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.ingestion.models import FetchedPrice
from src.storage.models import (
    DataQualityAlert,
    FedWatchSnapshot,
    NewsItem,
    PolymarketEvent,
    PriceRecord,
    SignalRecord,
)


async def save_price(
    session: AsyncSession,
    fetched: FetchedPrice,
    validation_status: str = "valid",
) -> PriceRecord:
    now = datetime.now(timezone.utc)
    record = PriceRecord(
        source=fetched.source,
        product_type=fetched.product_type,
        buy_price=fetched.buy_price,
        sell_price=fetched.sell_price,
        price_usd=fetched.price_usd,
        price_vnd=fetched.price_vnd,
        currency=fetched.currency,
        timestamp=fetched.timestamp,
        fetched_at=fetched.fetched_at or now,
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
    latest_fq = select(
        PriceRecord.source,
        PriceRecord.product_type,
        func.max(PriceRecord.fetched_at).label("max_fa"),
    ).group_by(PriceRecord.source, PriceRecord.product_type)
    if source:
        latest_fq = latest_fq.where(PriceRecord.source == source)
    if product_type:
        latest_fq = latest_fq.where(PriceRecord.product_type == product_type)
    latest_fq = latest_fq.subquery()

    stmt = (
        select(PriceRecord)
        .join(
            latest_fq,
            (PriceRecord.source == latest_fq.c.source)
            & (PriceRecord.product_type == latest_fq.c.product_type)
            & (PriceRecord.fetched_at == latest_fq.c.max_fa),
        )
        .order_by(PriceRecord.source, PriceRecord.product_type)
    )
    if source:
        stmt = stmt.where(PriceRecord.source == source)
    if product_type:
        stmt = stmt.where(PriceRecord.product_type == product_type)

    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_last_price_change_times(
    session: AsyncSession,
) -> dict[tuple[str, str], datetime]:
    latest = (
        select(
            PriceRecord.source,
            PriceRecord.product_type,
            func.max(PriceRecord.fetched_at).label("max_fa"),
        )
        .group_by(PriceRecord.source, PriceRecord.product_type)
        .subquery()
    )
    stmt = select(PriceRecord).join(
        latest,
        (PriceRecord.source == latest.c.source)
        & (PriceRecord.product_type == latest.c.product_type)
        & (PriceRecord.fetched_at == latest.c.max_fa),
    )
    result = await session.execute(stmt)
    current_rows = list(result.scalars().all())

    out: dict[tuple[str, str], datetime] = {}
    for row in current_rows:
        cur_sell = row.sell_price
        if cur_sell is None:
            continue
        sub = (
            select(PriceRecord.timestamp)
            .where(
                PriceRecord.source == row.source,
                PriceRecord.product_type == row.product_type,
                PriceRecord.sell_price == cur_sell,
            )
            .order_by(PriceRecord.timestamp.desc())
            .limit(1)
        )
        r = await session.execute(sub)
        changed_at = r.scalar()
        if changed_at:
            out[(row.source, row.product_type)] = changed_at
    return out


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


async def save_news_item(
    session: AsyncSession,
    title: str,
    url: str,
    source: str,
    published_at: datetime | None = None,
    excerpt: str | None = None,
    category: str | None = None,
    is_manual: bool = False,
) -> NewsItem | None:
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    stmt = sqlite_insert(NewsItem).values(
        title=title,
        url=url,
        source=source,
        published_at=published_at,
        excerpt=excerpt,
        category=category,
        is_manual=is_manual,
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["url"])
    result = await session.execute(stmt)
    await session.flush()
    if result.lastrowid:
        return await session.get(NewsItem, result.lastrowid)
    return None


async def get_recent_news(
    session: AsyncSession,
    limit: int = 20,
    category: str | None = None,
) -> list[NewsItem]:
    stmt = select(NewsItem).order_by(NewsItem.published_at.desc().nullslast())
    if category:
        stmt = stmt.where(NewsItem.category == category)
    stmt = stmt.limit(limit)
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def save_fedwatch_snapshot(
    session: AsyncSession, implied_rate: float, futures_price: float, contract: str
) -> FedWatchSnapshot:
    snapshot = FedWatchSnapshot(
        implied_rate=implied_rate,
        futures_price=futures_price,
        contract_symbol=contract,
    )
    session.add(snapshot)
    await session.flush()
    return snapshot


async def get_latest_fedwatch(session: AsyncSession) -> FedWatchSnapshot | None:
    from sqlalchemy import desc

    stmt = select(FedWatchSnapshot).order_by(desc(FedWatchSnapshot.id)).limit(1)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def save_polymarket_events(session: AsyncSession, events: list[dict]) -> int:
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    saved = 0
    for e in events:
        stmt = (
            sqlite_insert(PolymarketEvent)
            .values(
                slug=e["slug"],
                title=e["title"],
                question=e.get("question"),
                outcome_prices=e.get("outcome_prices"),
                volume_24h=e.get("volume_24h"),
                liquidity=e.get("liquidity"),
                one_day_price_change=e.get("one_day_price_change"),
                one_hour_price_change=e.get("one_hour_price_change"),
                category=e.get("category"),
                is_flagged=e.get("is_flagged", False),
            )
            .on_conflict_do_update(
                index_elements=["slug"],
                set_={
                    "title": e["title"],
                    "question": e.get("question"),
                    "outcome_prices": e.get("outcome_prices"),
                    "volume_24h": e.get("volume_24h"),
                    "liquidity": e.get("liquidity"),
                    "one_day_price_change": e.get("one_day_price_change"),
                    "one_hour_price_change": e.get("one_hour_price_change"),
                    "category": e.get("category"),
                    "is_flagged": e.get("is_flagged", False),
                    "fetched_at": func.now(),
                },
            )
        )
        await session.execute(stmt)
        saved += 1
    await session.flush()
    return saved


async def get_polymarket_events(
    session: AsyncSession, flagged_only: bool = False, limit: int = 20
) -> list[PolymarketEvent]:
    from sqlalchemy import desc

    stmt = (
        select(PolymarketEvent).order_by(desc(PolymarketEvent.fetched_at)).limit(limit)
    )
    if flagged_only:
        stmt = stmt.where(PolymarketEvent.is_flagged == True)
    result = await session.execute(stmt)
    return list(result.scalars().all())
