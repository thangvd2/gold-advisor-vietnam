from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

logging.getLogger("agentscope.formatter._openai_formatter").setLevel(logging.ERROR)

from src.api.routes.health import router as health_router, set_app_state
from src.config import VNTZ
from src.api.routes.quality import router as quality_router
from src.api.routes.gap import router as gap_router
from src.api.routes.prices import router as prices_router
from src.api.routes.signals import router as signals_router
from src.api.routes.dashboard import router as dashboard_router
from src.api.routes.admin import router as admin_router
from src.api.routes.news import router as news_router
from src.api.routes.chat import router as chat_router
from src.api.routes.polymarket import router as polymarket_router
from src.config import Settings
from src.ingestion.fetchers.dxy import DXYFetcher
from src.ingestion.fetchers.gold_price import YFinanceGoldFetcher
from src.ingestion.fetchers.vietcombank import VietcombankFxRateFetcher
from src.ingestion.scrapers.doji import DojiScraper
from src.ingestion.scrapers.phuquy import PhuQuyScraper
from src.ingestion.scrapers.sjc import SJCScraper
from src.ingestion.scrapers.pnj import PNJScraper
from src.ingestion.scrapers.btmc import BTMCScraper
from src.ingestion.scrapers.kimphat import KimPhatScraper
from src.ingestion.scheduler import start_scheduler, stop_scheduler
from src.alerts.bot import start_bot, stop_bot
from src.storage.database import init_db, async_session

BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _vn_time(value, fmt="%d/%m/%Y %H:%M"):
    if value is None:
        return "—"
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return value[:19] if len(value) >= 19 else value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(VNTZ).strftime(fmt)


templates.env.filters["vn_time"] = _vn_time

app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    settings = Settings()
    dxy_fetcher = DXYFetcher()
    gold_fetcher = YFinanceGoldFetcher()
    fx_fetcher = VietcombankFxRateFetcher()
    doji = DojiScraper()
    phuquy = PhuQuyScraper()
    sjc = SJCScraper()
    pnj = PNJScraper()
    btmc = BTMCScraper()
    kimphat = KimPhatScraper()
    vn_scrapers = [doji, phuquy, sjc, pnj, btmc, kimphat]
    sources = [gold_fetcher, dxy_fetcher] + vn_scrapers

    start_scheduler(app_state, sources, fx_fetcher, settings)
    await start_bot(settings.database_url)
    set_app_state(app_state)

    from src.ingestion.normalizer import fetch_and_store_all
    from src.ingestion.news.store import fetch_and_store_news

    try:
        await fetch_and_store_all(sources, fx_fetcher, settings)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Initial data fetch failed: {e}")

    news_feeds = [
        {"url": "https://vnexpress.net/rss/kinh-doanh.rss", "source": "VNExpress"},
        {"url": "https://tuoitre.vn/rss/kinh-doanh.rss", "source": "Tuoi Tre"},
        {
            "url": "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
            "source": "NYT",
        },
    ]
    try:
        await fetch_and_store_news(feeds=news_feeds, database_url=settings.database_url)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Initial news fetch failed: {e}")

    # Initial FedWatch fetch
    from src.ingestion.fetchers.fedwatch import FedWatchFetcher
    from src.storage.repository import save_fedwatch_snapshot

    try:
        fw_fetcher = FedWatchFetcher()
        fw_data = await fw_fetcher.fetch()
        if fw_data:
            async with async_session() as session:
                await save_fedwatch_snapshot(
                    session,
                    fw_data["implied_rate"],
                    fw_data["futures_price"],
                    fw_data["contract"],
                )
                await session.commit()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Initial FedWatch fetch failed: {e}")

    # Initial Polymarket fetch
    from src.ingestion.fetchers.polymarket import PolymarketFetcher
    from src.ingestion.polymarket.monitor import flag_significant_moves
    from src.storage.repository import save_polymarket_events

    try:
        pm_fetcher = PolymarketFetcher()
        pm_result = await pm_fetcher.fetch()
        pm_gold = pm_result.get("gold_macro", [])
        pm_movers = pm_result.get("market_movers", [])
        gold_slugs = {e["slug"] for e in pm_gold}
        pm_movers = [e for e in pm_movers if e["slug"] not in gold_slugs]
        for e in pm_gold:
            e["event_type"] = "gold_macro"
        for e in pm_movers:
            e["event_type"] = "market_mover"
        all_pm = pm_gold + pm_movers
        if all_pm:
            all_pm = flag_significant_moves(
                all_pm,
                settings.polymarket_move_threshold,
                settings.polymarket_volume_min,
            )
            async with async_session() as session:
                await save_polymarket_events(session, all_pm)
                await session.commit()
    except Exception as e:
        logging.getLogger(__name__).warning(f"Initial Polymarket fetch failed: {e}")

    yield
    await stop_bot()
    stop_scheduler(app_state)


app = FastAPI(title="Gold Advisor Vietnam", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
app.include_router(health_router)
app.include_router(quality_router, prefix="/quality", tags=["quality"])
app.include_router(gap_router, prefix="/api/gap", tags=["gap"])
app.include_router(prices_router, prefix="/api/prices", tags=["prices"])
app.include_router(signals_router, prefix="/api/signals", tags=["signals"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
app.include_router(news_router, prefix="/api/news", tags=["news"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(polymarket_router, prefix="/dashboard", tags=["polymarket"])


@app.get("/")
async def root(request: Request):
    return templates.TemplateResponse(request, "dashboard.html", context={})
