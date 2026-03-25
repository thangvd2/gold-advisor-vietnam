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
            {"url": "https://www.kitco.com/news/gold/rss", "source": "Kitco"},
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
    )
    scheduler.add_job(
        check_and_dispatch_alerts,
        "interval",
        minutes=settings.fetch_interval_minutes,
        args=[settings],
        id="alert_dispatch",
        replace_existing=True,
    )
    scheduler.add_job(
        fetch_news_job,
        "interval",
        minutes=settings.news_fetch_interval_minutes,
        args=[settings],
        id="news_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: gold_price_fetch + alert_dispatch every %d min, news_fetch every %d min",
        settings.fetch_interval_minutes,
        settings.news_fetch_interval_minutes,
    )


def stop_scheduler(app_state: dict) -> None:
    scheduler = app_state.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
