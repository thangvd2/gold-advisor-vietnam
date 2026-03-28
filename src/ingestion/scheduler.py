"""APScheduler job definitions for periodic gold price fetching."""

import asyncio
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import Settings
from src.ingestion.fetchers.fx_rate import FxRateFetcher

logger = logging.getLogger(__name__)

_dispatcher = None


def _get_db_path(settings: Settings) -> str:
    url = settings.database_url
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return url[len(prefix) :]
    return url


def check_and_dispatch_alerts(settings: Settings) -> None:
    global _dispatcher

    try:
        from src.alerts.dispatcher import AlertDispatcher
        from src.engine.pipeline import compute_signal
        from src.engine.types import SignalMode

        if _dispatcher is None:
            _dispatcher = AlertDispatcher()

        signal = compute_signal(_get_db_path(settings), SignalMode.SAVER)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(_dispatcher.check_signal(signal))
        finally:
            loop.close()
    except Exception:
        logger.exception("Alert dispatch failed")


def fetch_news_job(settings: Settings) -> None:
    try:
        from src.ingestion.news.store import fetch_and_store_news

        feeds = [
            {"url": "https://vnexpress.net/rss/kinh-doanh.rss", "source": "VNExpress"},
            {"url": "https://tuoitre.vn/rss/kinh-doanh.rss", "source": "Tuoi Tre"},
            {
                "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
                "source": "NYT",
            },
        ]

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(
                fetch_and_store_news(feeds=feeds, database_url=settings.database_url)
            )
        finally:
            loop.close()
    except Exception:
        logger.exception("News fetch failed")


def _fedwatch_sync(settings):
    from src.ingestion.fetchers.fedwatch import FedWatchFetcher
    from src.storage.database import async_session
    from src.storage.repository import save_fedwatch_snapshot

    fetcher = FedWatchFetcher()
    loop = asyncio.new_event_loop()
    try:
        data = loop.run_until_complete(fetcher.fetch())
        if data:

            async def _save():
                async with async_session() as session:
                    await save_fedwatch_snapshot(
                        session,
                        data["implied_rate"],
                        data["futures_price"],
                        data["contract"],
                    )
                    await session.commit()

            loop2 = asyncio.new_event_loop()
            try:
                loop2.run_until_complete(_save())
            finally:
                loop2.close()
    except Exception as e:
        logger.warning("FedWatch fetch failed: %s", e)
    finally:
        loop.close()


def _polymarket_sync(settings):
    import json

    from src.ingestion.fetchers.polymarket import PolymarketFetcher
    from src.ingestion.polymarket.monitor import flag_significant_moves
    from src.storage.database import async_session
    from src.storage.repository import (
        get_previous_snapshots,
        get_recent_news,
        save_polymarket_events,
        save_price_snapshots,
        save_smart_signal,
    )

    fetcher = PolymarketFetcher()
    loop = asyncio.new_event_loop()
    try:
        result = loop.run_until_complete(fetcher.fetch())
        gold_macro = result.get("gold_macro", [])
        market_movers = result.get("market_movers", [])
        gold_slugs = {e["slug"] for e in gold_macro}
        market_movers = [e for e in market_movers if e["slug"] not in gold_slugs]

        for e in gold_macro:
            e["event_type"] = "gold_macro"
        for e in market_movers:
            e["event_type"] = "market_mover"

        all_events = gold_macro + market_movers
        if all_events:
            all_events = flag_significant_moves(
                all_events,
                settings.polymarket_move_threshold,
                settings.polymarket_volume_min,
            )

            snapshots = []
            for e in all_events:
                yes_price = None
                raw_prices = e.get("outcome_prices")
                if raw_prices:
                    try:
                        prices = (
                            json.loads(raw_prices)
                            if isinstance(raw_prices, str)
                            else raw_prices
                        )
                        if prices:
                            yes_price = float(prices[0])
                    except (ValueError, TypeError, IndexError):
                        pass
                if yes_price is None:
                    continue
                snapshots.append(
                    {
                        "slug": e["slug"],
                        "title": e["title"],
                        "yes_price": yes_price,
                        "volume_24h": e.get("volume_24h"),
                        "liquidity": e.get("liquidity"),
                        "one_day_change": e.get("one_day_price_change"),
                        "category": e.get("category"),
                    }
                )

            async def _save():
                async with async_session() as session:
                    count = await save_polymarket_events(session, all_events)
                    logger.info(
                        "Polymarket: saved %d events (%d gold_macro, %d market_movers), %d flagged",
                        count,
                        len(gold_macro),
                        len(market_movers),
                        sum(1 for e in all_events if e.get("is_flagged")),
                    )

                    if snapshots:
                        snap_count = await save_price_snapshots(session, snapshots)
                        logger.info("Polymarket: saved %d price snapshots", snap_count)

                        prev_snapshots = await get_previous_snapshots(session)
                        if prev_snapshots:
                            from src.ingestion.polymarket.smart_money import (
                                detect_smart_moves,
                            )

                            recent_news_rows = await get_recent_news(session, limit=50)
                            recent_news = [
                                {
                                    "title": n.title,
                                    "excerpt": n.excerpt or "",
                                    "published_at": n.published_at,
                                }
                                for n in recent_news_rows
                            ]

                            new_snap_dicts = [
                                {k: v for k, v in s.items()} for s in snapshots
                            ]
                            prev_snap_dicts = [
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
                                for s in prev_snapshots
                            ]

                            signals = detect_smart_moves(
                                new_snap_dicts, prev_snap_dicts, recent_news
                            )
                            for sig in signals:
                                await save_smart_signal(session, sig)
                                logger.info(
                                    "Smart money signal: %s (%s) — %s, %.1f¢ %s",
                                    sig["title"][:40],
                                    sig["signal_type"],
                                    sig["confidence"],
                                    sig["move_cents"],
                                    sig["move_direction"],
                                )

                    await session.commit()

            loop2 = asyncio.new_event_loop()
            try:
                loop2.run_until_complete(_save())
            finally:
                loop2.close()
    except Exception:
        logger.warning("Polymarket sync failed", exc_info=True)
    finally:
        loop.close()


def _fetch_all_sync(sources, fx_fetcher, settings):
    """Sync wrapper for async fetch_and_store_all, called by BackgroundScheduler."""
    from src.ingestion.normalizer import fetch_and_store_all

    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(fetch_and_store_all(sources, fx_fetcher, settings))
    finally:
        loop.close()


def start_scheduler(
    app_state: dict,
    sources: list,
    fx_fetcher: FxRateFetcher,
    settings: Settings,
) -> None:
    scheduler = BackgroundScheduler()
    app_state["scheduler"] = scheduler

    scheduler.add_job(
        _fetch_all_sync,
        "interval",
        minutes=settings.fetch_interval_minutes,
        args=[sources, fx_fetcher, settings],
        id="gold_price_fetch",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        check_and_dispatch_alerts,
        "interval",
        minutes=settings.fetch_interval_minutes,
        args=[settings],
        id="alert_dispatch",
        replace_existing=True,
        misfire_grace_time=120,
    )
    scheduler.add_job(
        fetch_news_job,
        "interval",
        minutes=settings.news_fetch_interval_minutes,
        args=[settings],
        id="news_fetch",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _fedwatch_sync,
        "interval",
        minutes=settings.fedwatch_fetch_interval_minutes,
        args=[settings],
        id="fedwatch_fetch",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.add_job(
        _polymarket_sync,
        "interval",
        minutes=settings.polymarket_fetch_interval_minutes,
        args=[settings],
        id="polymarket_fetch",
        replace_existing=True,
        misfire_grace_time=300,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: gold_price_fetch + alert_dispatch every %d min, news_fetch every %d min, fedwatch_fetch every %d min, polymarket_fetch every %d min",
        settings.fetch_interval_minutes,
        settings.news_fetch_interval_minutes,
        settings.fedwatch_fetch_interval_minutes,
        settings.polymarket_fetch_interval_minutes,
    )


def stop_scheduler(app_state: dict) -> None:
    scheduler = app_state.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
