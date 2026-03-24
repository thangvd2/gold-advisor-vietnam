import os
import tempfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base, NewsItem


@pytest.fixture
def news_test_app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)

    with engine.connect() as conn:
        conn.execute(
            __import__("sqlalchemy").text(
                "INSERT INTO news_items (title, url, source, published_at, category, is_manual) VALUES "
                "('Gold up 5%', 'https://a.com/1', 'Reuters', '2026-03-25T10:00:00Z', 'gold_market', 0),"
                "('SBV auction', 'https://sbv.gov.vn/1', 'State Bank', '2026-03-25T08:00:00Z', 'state_bank', 0),"
                "('Gold flat', 'https://a.com/2', 'Bloomberg', '2026-03-24T10:00:00Z', 'gold_market', 0)"
            )
        )
        conn.commit()

    def mock_settings():
        from src.config import Settings

        return Settings(database_url=f"sqlite:///{path}")

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    async_test_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.api.routes.news.get_settings", mock_settings
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.api.routes.news.async_session", async_test_session
        ),
    ):
        from fastapi import FastAPI
        from src.api.routes.news import router

        app = FastAPI()
        app.include_router(router, prefix="/api/news", tags=["news"])
        client = TestClient(app)

        yield client

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_engine.dispose())
    os.unlink(path)


class TestNewsAPI:
    def test_get_news_returns_200(self, news_test_app):
        resp = news_test_app.get("/api/news")
        assert resp.status_code == 200

    def test_get_news_returns_list(self, news_test_app):
        resp = news_test_app.get("/api/news")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 3

    def test_get_news_has_required_fields(self, news_test_app):
        resp = news_test_app.get("/api/news")
        data = resp.json()
        article = data[0]
        assert "id" in article
        assert "title" in article
        assert "url" in article
        assert "source" in article
        assert "published_at" in article

    def test_get_news_respects_limit(self, news_test_app):
        resp = news_test_app.get("/api/news?limit=2")
        data = resp.json()
        assert len(data) == 2

    def test_get_news_filter_by_category(self, news_test_app):
        resp = news_test_app.get("/api/news?category=state_bank")
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "State Bank"

    def test_get_news_sorted_newest_first(self, news_test_app):
        resp = news_test_app.get("/api/news")
        data = resp.json()
        dates = [a["published_at"] for a in data if a["published_at"]]
        assert dates == sorted(dates, reverse=True)


class TestNewsAPISingle:
    def test_get_single_news_200(self, news_test_app):
        resp = news_test_app.get("/api/news/1")
        assert resp.status_code == 200
        assert resp.json()["title"] == "Gold up 5%"

    def test_get_single_news_404(self, news_test_app):
        resp = news_test_app.get("/api/news/9999")
        assert resp.status_code == 404
