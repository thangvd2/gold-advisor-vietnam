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
    from src.config import Settings
    from src.ingestion.fetchers.polymarket import PolymarketFetcher
    from src.ingestion.polymarket.monitor import flag_significant_moves
    from src.storage.database import async_session
    from src.storage.repository import save_polymarket_events

    fetcher = PolymarketFetcher()
    loop = asyncio.new_event_loop()
    try:
        events = loop.run_until_complete(fetcher.fetch())
        if events:
            s = Settings()
            events = flag_significant_moves(
                events, s.polymarket_move_threshold, s.polymarket_volume_min
            )

            async def _save():
                async with async_session() as session:
                    count = await save_polymarket_events(session, events)
                    logger.info(
                        "Polymarket: saved %d events, %d flagged",
                        count,
                        sum(1 for e in events if e.get("is_flagged")),
                    )
                    await session.commit()

            loop2 = asyncio.new_event_loop()
            try:
                loop2.run_until_complete(_save())
            finally:
                loop2.close()
    except Exception as e:
        logger.warning("Polymarket fetch failed: %s", e)
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
