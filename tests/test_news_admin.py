import os
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base


@pytest.fixture
def admin_news_app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)

    def mock_settings():
        from src.config import Settings

        return Settings(database_url=f"sqlite:///{path}")

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    async_test_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    with (
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.api.routes.admin.get_settings", mock_settings
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.api.routes.admin.async_session", async_test_session
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.api.routes.news.get_settings", mock_settings
        ),
        __import__("unittest.mock", fromlist=["patch"]).patch(
            "src.api.routes.news.async_session", async_test_session
        ),
    ):
        from fastapi import FastAPI
        from src.api.routes.admin import router as admin_router
        from src.api.routes.news import router as news_router

        app = FastAPI()
        app.include_router(admin_router, prefix="/api/admin", tags=["admin"])
        app.include_router(news_router, prefix="/api/news", tags=["news"])
        client = TestClient(app)

        yield client

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_engine.dispose())
    os.unlink(path)


class TestAdminNewsCreate:
    def test_create_manual_news(self, admin_news_app):
        resp = admin_news_app.post(
            "/api/admin/news",
            json={
                "title": "SBV announces gold auction",
                "source": "State Bank of Vietnam",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "SBV announces gold auction"
        assert data["source"] == "State Bank of Vietnam"
        assert data["is_manual"] is True
        assert data["category"] == "state_bank"

    def test_create_with_optional_fields(self, admin_news_app):
        resp = admin_news_app.post(
            "/api/admin/news",
            json={
                "title": "Custom news",
                "url": "https://example.com/custom",
                "source": "Admin",
                "published_at": "2026-03-25T10:00:00+00:00",
                "excerpt": "This is a test news item.",
                "category": "gold_market",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["url"] == "https://example.com/custom"
        assert data["excerpt"] == "This is a test news item."
        assert data["category"] == "gold_market"
        assert data["published_at"] is not None

    def test_title_required(self, admin_news_app):
        resp = admin_news_app.post(
            "/api/admin/news",
            json={"source": "Admin"},
        )
        assert resp.status_code == 422

    def test_source_required(self, admin_news_app):
        resp = admin_news_app.post(
            "/api/admin/news",
            json={"title": "Test"},
        )
        assert resp.status_code == 422

    def test_manual_news_appears_in_feed(self, admin_news_app):
        admin_news_app.post(
            "/api/admin/news",
            json={
                "title": "SBV gold auction notice",
                "source": "State Bank",
                "category": "state_bank",
            },
        )
        resp = admin_news_app.get("/api/news?category=state_bank")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) >= 1
        assert any(d["title"] == "SBV gold auction notice" for d in data)
