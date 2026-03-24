import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base


def _create_app_with_news(path: str):
    from unittest.mock import patch

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    async_test_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    def mock_settings():
        from src.config import Settings

        return Settings(database_url=f"sqlite:///{path}")

    with (
        patch("src.api.routes.dashboard.get_settings", mock_settings),
        patch("src.api.routes.dashboard.async_session", async_test_session),
    ):
        from fastapi import FastAPI
        from src.api.routes.dashboard import router

        app = FastAPI()
        app.include_router(router, prefix="/dashboard", tags=["dashboard"])
        client = TestClient(app)
        yield client, async_engine


class TestNewsDashboardAPI:
    @pytest.fixture
    def app_with_news(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)

        with engine.connect() as conn:
            conn.execute(
                __import__("sqlalchemy").text(
                    "INSERT INTO news_items (title, url, source, published_at, category, is_manual) VALUES "
                    "('Gold up 5%', 'https://a.com/1', 'Reuters', '2026-03-25T10:00:00Z', 'gold_market', 0),"
                    "('SBV auction next week', 'https://sbv.gov.vn/1', 'State Bank', '2026-03-25T08:00:00Z', 'state_bank', 1)"
                )
            )
            conn.commit()

        for client, async_engine in _create_app_with_news(path):
            yield client

        import asyncio

        asyncio.get_event_loop().run_until_complete(async_engine.dispose())
        engine.dispose()
        os.unlink(path)

    def test_news_json_endpoint_200(self, app_with_news):
        resp = app_with_news.get("/dashboard/news")
        assert resp.status_code == 200

    def test_news_json_returns_articles(self, app_with_news):
        resp = app_with_news.get("/dashboard/news")
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_news_json_has_required_fields(self, app_with_news):
        resp = app_with_news.get("/dashboard/news")
        data = resp.json()
        for article in data:
            assert "title" in article
            assert "url" in article
            assert "source" in article
            assert "published_at" in article

    def test_news_json_empty_when_no_data(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)

        for client, async_engine in _create_app_with_news(path):
            resp = client.get("/dashboard/news")
            assert resp.status_code == 200
            assert resp.json() == []

        import asyncio

        asyncio.get_event_loop().run_until_complete(async_engine.dispose())
        engine.dispose()
        os.unlink(path)

    def test_news_partial_returns_html(self, app_with_news):
        resp = app_with_news.get("/dashboard/partials/news")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")

    def test_news_partial_contains_headlines(self, app_with_news):
        resp = app_with_news.get("/dashboard/partials/news")
        html = resp.text
        assert "Gold up 5%" in html
        assert "SBV auction next week" in html

    def test_news_partial_contains_state_bank_badge(self, app_with_news):
        resp = app_with_news.get("/dashboard/partials/news")
        html = resp.text
        assert "State Bank" in html

    def test_news_partial_empty_state(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)

        for client, async_engine in _create_app_with_news(path):
            resp = client.get("/dashboard/partials/news")
            assert resp.status_code == 200
            assert "No news" in resp.text

        import asyncio

        asyncio.get_event_loop().run_until_complete(async_engine.dispose())
        engine.dispose()
        os.unlink(path)
