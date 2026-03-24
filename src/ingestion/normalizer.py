"""Normalizer pipeline: fetch → convert → store → quality check."""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from src.config import Settings
from src.ingestion.fetchers.base import DataSource
from src.ingestion.fetchers.fx_rate import FxRateFetcher
from src.ingestion.models import convert_usd_to_vnd_per_luong
from src.ingestion.quality import check_anomaly, check_missing, run_quality_checks
from src.storage.database import async_session
from src.storage.repository import save_price

logger = logging.getLogger(__name__)


async def fetch_and_store(
    session: AsyncSession,
    gold_fetcher: DataSource,
    fx_fetcher: FxRateFetcher,
    settings: Settings,
) -> dict:
    source = gold_fetcher.__class__.__name__.replace("Fetcher", "").lower()

    try:
        prices = await gold_fetcher.fetch()
    except Exception as exc:
        logger.error("Fetcher %s failed: %s", source, exc, exc_info=True)
        await check_missing(session, source=source, product_type="xau_usd")
        await session.commit()
        return {"status": "failed", "alerts": 1, "error": str(exc)}

    if not prices:
        await check_missing(session, source=source, product_type="xau_usd")
        await session.commit()
        return {"status": "failed", "alerts": 1}

    vnd_rate = None
    try:
        fx_prices = await fx_fetcher.fetch()
        if fx_prices:
            vnd_rate = fx_prices[0].sell_price
    except Exception:
        logger.warning("FX fetch failed, skipping VND conversion", exc_info=True)

    saved_records = []
    alert_count = 0

    for fetched_price in prices:
        if vnd_rate and fetched_price.price_usd and fetched_price.currency == "USD":
            fetched_price.price_vnd = convert_usd_to_vnd_per_luong(
                fetched_price.price_usd, vnd_rate
            )

        record = await save_price(session, fetched_price, validation_status="valid")
        saved_records.append(record)

        anomaly_alert = await check_anomaly(
            session,
            new_record=record,
            threshold_percent=settings.anomaly_threshold_percent,
        )
        if anomaly_alert:
            record.validation_status = "warning"
            alert_count += 1

    freshness_alerts = await run_quality_checks(
        session,
        source=prices[0].source if prices else source,
        product_type=prices[0].product_type if prices else "xau_usd",
        threshold_minutes=settings.freshness_threshold_minutes,
    )
    alert_count += len(freshness_alerts)

    await session.commit()
    return {"status": "ok", "prices_saved": len(saved_records), "alerts": alert_count}


async def fetch_and_store_all(
    sources: list[DataSource],
    fx_fetcher: FxRateFetcher,
    settings: Settings,
) -> dict:
    total_saved = 0
    total_alerts = 0
    statuses = []

    async with async_session() as session:
        for source in sources:
            result = await fetch_and_store(session, source, fx_fetcher, settings)
            total_saved += result.get("prices_saved", 0)
            total_alerts += result.get("alerts", 0)
            statuses.append(result)

    return {
        "status": "ok" if all(s["status"] == "ok" for s in statuses) else "partial",
        "total_saved": total_saved,
        "total_alerts": total_alerts,
        "details": statuses,
    }
