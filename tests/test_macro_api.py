import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.storage.models import Base, PriceRecord


@pytest.fixture
def macro_test_app():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        for i in range(40):
            ts = now - timedelta(days=40 - i)
            session.add(
                PriceRecord(
                    source="vietcombank",
                    product_type="usd_vnd",
                    sell_price=24000.0 + i * 100.0,
                    currency="VND",
                    timestamp=ts,
                )
            )
            session.add(
                PriceRecord(
                    source="yfinance",
                    product_type="xau_usd",
                    price_usd=2400.0 + i * 10.0,
                    currency="USD",
                    timestamp=ts,
                )
            )
            session.add(
                PriceRecord(
                    source="yfinance",
                    product_type="dxy",
                    price_usd=104.0 + i * 0.05,
                    currency="USD",
                    timestamp=ts,
                )
            )
        session.commit()

    from unittest.mock import patch, MagicMock

    def mock_settings():
        from src.config import Settings

        return Settings(database_url=f"sqlite:///{path}")

    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    async_test_session = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    with (
        patch("src.api.routes.dashboard.get_settings", mock_settings),
        patch("src.api.routes.dashboard.async_session", async_test_session),
    ):
        from fastapi import FastAPI
        from src.api.routes.dashboard import router

        app = FastAPI()
        app.include_router(router, prefix="/dashboard", tags=["dashboard"])
        client = TestClient(app)

        yield client

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_engine.dispose())

    os.unlink(path)


class TestMacroAPI:
    def test_macro_endpoint_returns_200(self, macro_test_app):
        resp = macro_test_app.get("/dashboard/macro")
        assert resp.status_code == 200

    def test_macro_response_has_fx_trend(self, macro_test_app):
        resp = macro_test_app.get("/dashboard/macro")
        data = resp.json()
        assert "fx_trend" in data
        assert "current_rate" in data["fx_trend"]
        assert "trend" in data["fx_trend"]

    def test_macro_response_has_gold_trend(self, macro_test_app):
        resp = macro_test_app.get("/dashboard/macro")
        data = resp.json()
        assert "gold_trend" in data
        assert "current_price" in data["gold_trend"]
        assert "trend" in data["gold_trend"]

    def test_macro_response_has_dxy(self, macro_test_app):
        resp = macro_test_app.get("/dashboard/macro")
        data = resp.json()
        assert "dxy" in data
        assert data["dxy"] is not None


class TestMacroAPIEmpty:
    @pytest.fixture
    def empty_app(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)

        from unittest.mock import patch
        from sqlalchemy.ext.asyncio import (
            AsyncSession,
            async_sessionmaker,
            create_async_engine,
        )

        def mock_settings():
            from src.config import Settings

            return Settings(database_url=f"sqlite:///{path}")

        async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
        async_test_session = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )

        with (
            patch("src.api.routes.dashboard.get_settings", mock_settings),
            patch("src.api.routes.dashboard.async_session", async_test_session),
        ):
            from fastapi import FastAPI
            from src.api.routes.dashboard import router

            app = FastAPI()
            app.include_router(router, prefix="/dashboard", tags=["dashboard"])
            client = TestClient(app)

            yield client

        import asyncio

        asyncio.get_event_loop().run_until_complete(async_engine.dispose())
        os.unlink(path)

    def test_macro_returns_empty_data_gracefully(self, empty_app):
        resp = empty_app.get("/dashboard/macro")
        assert resp.status_code == 200
        data = resp.json()
        assert data["fx_trend"] is None
        assert data["gold_trend"] is None
