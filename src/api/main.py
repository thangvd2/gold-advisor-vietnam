from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api.routes.health import router as health_router
from src.storage.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Gold Advisor Vietnam", lifespan=lifespan)
app.include_router(health_router)
