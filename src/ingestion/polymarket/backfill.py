import logging
import time
from datetime import datetime, timedelta, timezone

import httpx

logger = logging.getLogger(__name__)

GAP_THRESHOLD_SECONDS = 3600


async def run_gap_backfill(settings) -> dict:
    from src.alerts.dispatcher import AlertDispatcher
    from src.ingestion.fetchers.polymarket_clob import (
        fetch_price_history,
        fetch_price_history_fallback,
    )
    from src.ingestion.polymarket.smart_money import detect_smart_moves
    from src.storage.database import async_session
    from src.storage.repository import (
        get_events_with_clob_tokens,
        get_latest_snapshot_ts_per_slug,
        get_previous_snapshots,
        get_recent_news,
        save_price_snapshots_backfill,
        save_smart_signal,
    )

    now = datetime.now(timezone.utc)
    now_ts = int(now.timestamp())
    max_backfill_seconds = settings.polymarket_backfill_max_days * 86400
    default_lookback_seconds = settings.polymarket_backfill_default_hours * 3600
    fidelity = settings.polymarket_backfill_fidelity

    events_processed = 0
    snapshots_saved = 0
    signals_detected = 0
    all_backfilled_snapshots: list[dict] = []
    earliest_backfilled_ts: dict[str, datetime] = {}

    async with async_session() as session:
        events = await get_events_with_clob_tokens(session)

    if not events:
        logger.info("Gap backfill: no events with CLOB tokens")
        return {"events_processed": 0, "snapshots_saved": 0, "signals_detected": 0}

    slugs = {e.slug for e in events}

    async with async_session() as session:
        latest_ts_map = await get_latest_snapshot_ts_per_slug(session, slugs)

    async with httpx.AsyncClient() as client:
        for event in events:
            token_id = event.clob_token_id_yes
            if not token_id:
                continue

            latest_ts = latest_ts_map.get(event.slug)
            if latest_ts is None:
                start_ts = now_ts - default_lookback_seconds
            else:
                if latest_ts.tzinfo is None:
                    latest_ts = latest_ts.replace(tzinfo=timezone.utc)
                gap_seconds = (now - latest_ts).total_seconds()
                if gap_seconds <= GAP_THRESHOLD_SECONDS:
                    logger.debug(
                        "Skipping %s: gap %.0fs < threshold",
                        event.slug,
                        gap_seconds,
                    )
                    continue
                start_ts = int(latest_ts.timestamp())

            capped_start_ts = now_ts - max_backfill_seconds
            if start_ts < capped_start_ts:
                start_ts = capped_start_ts

            if start_ts >= now_ts:
                continue

            try:
                points = await fetch_price_history(
                    client, token_id, start_ts, now_ts, fidelity
                )
                if not points:
                    points = await fetch_price_history_fallback(client, token_id)

                if not points:
                    logger.debug("No CLOB data for %s in gap period", event.slug)
                    continue

                snapshots = []
                for pt in points:
                    fetched_at = datetime.fromtimestamp(pt.t, tz=timezone.utc)
                    snapshots.append(
                        {
                            "slug": event.slug,
                            "title": event.title,
                            "yes_price": pt.p,
                            "category": event.category,
                            "fetched_at": fetched_at,
                        }
                    )

                async with async_session() as session:
                    count = await save_price_snapshots_backfill(session, snapshots)
                    await session.commit()

                snapshots_saved += count
                events_processed += 1
                all_backfilled_snapshots.extend(snapshots)

                event_timestamps = [s["fetched_at"] for s in snapshots]
                earliest_backfilled_ts[event.slug] = min(event_timestamps)

                logger.info(
                    "Backfilled %d snapshots for %s (gap from %s to now)",
                    count,
                    event.slug,
                    start_ts,
                )
            except Exception:
                logger.warning("Gap backfill failed for %s", event.slug, exc_info=True)

    if not all_backfilled_snapshots:
        return {
            "events_processed": events_processed,
            "snapshots_saved": snapshots_saved,
            "signals_detected": 0,
        }

    try:
        post_backfill = _build_post_backfill_dicts(all_backfilled_snapshots)

        pre_gap = []
        async with async_session() as session:
            recent_news_rows = await get_recent_news(session, limit=50)
        recent_news = [
            {
                "title": n.title,
                "excerpt": n.excerpt or "",
                "published_at": n.published_at,
            }
            for n in recent_news_rows
        ]

        if earliest_backfilled_ts:
            earliest_overall = min(earliest_backfilled_ts.values())
            lookback_start = earliest_overall - timedelta(hours=2)
            async with async_session() as session:
                cutoff_snapshots = await _get_pre_gap_snapshots(session, lookback_start)
            pre_gap = [
                {
                    "slug": s.slug,
                    "title": s.title,
                    "yes_price": s.yes_price,
                    "volume_24h": s.volume_24h,
                    "liquidity": s.liquidity,
                    "one_day_change": s.one_day_change,
                    "category": s.category,
                    "fetched_at": s.fetched_at,
                }
                for s in cutoff_snapshots
            ]

        signals = detect_smart_moves(post_backfill, pre_gap, recent_news)

        for sig in signals:
            async with async_session() as session:
                await save_smart_signal(session, sig)
                await session.commit()

        signals_detected = len(signals)

        if signals:
            dispatcher = AlertDispatcher()
            await dispatcher.dispatch_smart_money_alerts(signals)

        logger.info(
            "Gap backfill smart money: %d signals from %d backfilled snapshots",
            signals_detected,
            snapshots_saved,
        )
    except Exception:
        logger.warning("Smart money detection after backfill failed", exc_info=True)

    return {
        "events_processed": events_processed,
        "snapshots_saved": snapshots_saved,
        "signals_detected": signals_detected,
    }


def _build_post_backfill_dicts(snapshots: list[dict]) -> list[dict]:
    latest_per_slug: dict[str, dict] = {}
    for s in snapshots:
        slug = s["slug"]
        if (
            slug not in latest_per_slug
            or s["fetched_at"] > latest_per_slug[slug]["fetched_at"]
        ):
            latest_per_slug[slug] = s
    return list(latest_per_slug.values())


async def _get_pre_gap_snapshots(session, before: datetime):
    from sqlalchemy import desc, select

    from src.storage.models import PolymarketPriceSnapshot

    stmt = (
        select(PolymarketPriceSnapshot)
        .where(PolymarketPriceSnapshot.fetched_at < before)
        .order_by(desc(PolymarketPriceSnapshot.fetched_at))
        .limit(500)
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
