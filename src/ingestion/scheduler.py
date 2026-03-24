"""APScheduler job definitions for periodic gold price fetching."""

import logging

from apscheduler.schedulers.background import BackgroundScheduler

from src.config import Settings
from src.ingestion.fetchers.fx_rate import FxRateFetcher

logger = logging.getLogger(__name__)


def start_scheduler(
    app_state: dict,
    sources: list,
    fx_fetcher: FxRateFetcher,
    settings: Settings,
) -> None:
    scheduler = BackgroundScheduler()
    app_state["scheduler"] = scheduler

    from src.ingestion.normalizer import fetch_and_store_all

    scheduler.add_job(
        fetch_and_store_all,
        "interval",
        minutes=settings.fetch_interval_minutes,
        args=[sources, fx_fetcher, settings],
        id="gold_price_fetch",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(
        "Scheduler started: gold_price_fetch every %d minutes",
        settings.fetch_interval_minutes,
    )


def stop_scheduler(app_state: dict) -> None:
    scheduler = app_state.get("scheduler")
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped")
