from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes.health import router as health_router, set_app_state
from src.api.routes.quality import router as quality_router
from src.config import Settings
from src.ingestion.fetchers.gold_price import YFinanceGoldFetcher
from src.ingestion.fetchers.vietcombank import VietcombankFxRateFetcher
from src.ingestion.scrapers.doji import DojiScraper
from src.ingestion.scrapers.phuquy import PhuQuyScraper
from src.ingestion.scrapers.sjc import SJCScraper
from src.ingestion.scrapers.pnj import PNJScraper
from src.ingestion.scrapers.btmc import BTMCScraper
from src.ingestion.scheduler import start_scheduler, stop_scheduler
from src.storage.database import init_db

app_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()

    settings = Settings()
    gold_fetcher = YFinanceGoldFetcher()
    fx_fetcher = VietcombankFxRateFetcher()
    doji = DojiScraper()
    phuquy = PhuQuyScraper()
    sjc = SJCScraper()
    pnj = PNJScraper()
    btmc = BTMCScraper()
    vn_scrapers = [doji, phuquy, sjc, pnj, btmc]
    sources = [gold_fetcher] + vn_scrapers

    start_scheduler(app_state, sources, fx_fetcher, settings)
    set_app_state(app_state)
    yield
    stop_scheduler(app_state)


app = FastAPI(title="Gold Advisor Vietnam", lifespan=lifespan)
app.include_router(health_router)
app.include_router(quality_router, prefix="/quality", tags=["quality"])
