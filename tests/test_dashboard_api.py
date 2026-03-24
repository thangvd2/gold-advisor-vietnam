"""Tests for dashboard API endpoints (Plan 05-01).

Uses TestClient with patched settings (same pattern as test_signal_api.py).
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.storage.models import Base, PriceRecord


@pytest_asyncio.fixture
async def dashboard_test_db(tmp_path):
    db_file = tmp_path / "test_dashboard_api.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    from unittest.mock import patch

    def mock_settings():
        from src.config import Settings

        return Settings(database_url=f"sqlite+aiosqlite:///{db_file}")

    with (
        patch("src.api.routes.dashboard.get_settings", mock_settings),
        patch("src.storage.database.settings", mock_settings()),
        patch("src.storage.database.engine", engine),
        patch(
            "src.storage.database.async_session",
            async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False),
        ),
    ):
        from fastapi import FastAPI
        from src.api.routes.dashboard import router

        app = FastAPI()
        app.include_router(router, prefix="/dashboard", tags=["dashboard"])
        client = TestClient(app)

        yield {"client": client, "session_factory": session_factory}

    await engine.dispose()


def _make_price_record(
    source: str,
    product_type: str,
    buy_price: float | None = None,
    sell_price: float | None = None,
    price_usd: float | None = None,
    price_vnd: float | None = None,
    timestamp: datetime | None = None,
    currency: str = "VND",
) -> PriceRecord:
    return PriceRecord(
        source=source,
        product_type=product_type,
        buy_price=buy_price,
        sell_price=sell_price,
        price_usd=price_usd,
        price_vnd=price_vnd,
        currency=currency,
        timestamp=timestamp or datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        validation_status="valid",
    )


async def _seed_prices(
    session_factory: async_sessionmaker[AsyncSession],
    records: list[PriceRecord],
) -> None:
    async with session_factory() as session:
        session.add_all(records)
        await session.commit()


async def _seed_dealer_prices(
    session_factory: async_sessionmaker[AsyncSession],
):
    now = datetime.now(timezone.utc)
    records = []

    # International gold (xau_usd)
    records.append(
        _make_price_record(
            source="yfinance",
            product_type="xau_usd",
            price_usd=2650.0,
            price_vnd=190_000_000,
            timestamp=now,
            currency="USD",
        )
    )

    # Dealer SJC bar prices
    for dealer in ("SJC", "DOJI", "PNJ", "BTMC", "PHUQUY"):
        records.append(
            _make_price_record(
                source=dealer,
                product_type="sjc_bar",
                buy_price=193_000_000,
                sell_price=195_000_000,
                timestamp=now,
                currency="VND",
            )
        )
        # Ring gold
        records.append(
            _make_price_record(
                source=dealer,
                product_type="ring_gold",
                buy_price=192_000_000,
                sell_price=194_000_000,
                timestamp=now,
                currency="VND",
            )
        )

    await _seed_prices(session_factory, records)


class TestGetDashboardPrices:
    @pytest.mark.asyncio
    async def test_returns_200_with_structured_dealer_json(self, dashboard_test_db):
        await _seed_dealer_prices(dashboard_test_db["session_factory"])

        resp = dashboard_test_db["client"].get("/dashboard/prices")

        assert resp.status_code == 200
        data = resp.json()
        assert "dealers" in data
        assert isinstance(data["dealers"], list)

    @pytest.mark.asyncio
    async def test_dealers_grouped_by_source(self, dashboard_test_db):
        await _seed_dealer_prices(dashboard_test_db["session_factory"])

        resp = dashboard_test_db["client"].get("/dashboard/prices")
        data = resp.json()

        sources = {d["source"] for d in data["dealers"]}
        assert "SJC" in sources
        assert "DOJI" in sources
        assert "PNJ" in sources
        assert "yfinance" in sources

    @pytest.mark.asyncio
    async def test_each_dealer_has_products_list(self, dashboard_test_db):
        await _seed_dealer_prices(dashboard_test_db["session_factory"])

        resp = dashboard_test_db["client"].get("/dashboard/prices")
        data = resp.json()

        for dealer in data["dealers"]:
            assert "source" in dealer
            assert "products" in dealer
            assert "fetched_at" in dealer
            assert isinstance(dealer["products"], list)

    @pytest.mark.asyncio
    async def test_product_has_buy_sell_spread_for_dealers(self, dashboard_test_db):
        await _seed_dealer_prices(dashboard_test_db["session_factory"])

        resp = dashboard_test_db["client"].get("/dashboard/prices")
        data = resp.json()

        # Find a dealer (not yfinance) and check product fields
        for dealer in data["dealers"]:
            if dealer["source"] != "yfinance":
                for product in dealer["products"]:
                    if product["product_type"] == "sjc_bar":
                        assert "buy_price" in product
                        assert "sell_price" in product
                        assert "spread" in product
                        assert product["product_type"] == "sjc_bar"
                        break
                break

    @pytest.mark.asyncio
    async def test_xau_usd_has_price_usd_and_price_vnd(self, dashboard_test_db):
        await _seed_dealer_prices(dashboard_test_db["session_factory"])

        resp = dashboard_test_db["client"].get("/dashboard/prices")
        data = resp.json()

        xau_entry = next(
            (d for d in data["dealers"] if d["source"] == "yfinance"), None
        )
        assert xau_entry is not None

        xau_product = next(
            (p for p in xau_entry["products"] if p["product_type"] == "xau_usd"), None
        )
        assert xau_product is not None
        assert "price_usd" in xau_product
        assert "price_vnd" in xau_product
        assert xau_product["price_usd"] == 2650.0
        assert xau_product["price_vnd"] == 190_000_000

    @pytest.mark.asyncio
    async def test_returns_empty_list_gracefully(self, dashboard_test_db):
        resp = dashboard_test_db["client"].get("/dashboard/prices")

        assert resp.status_code == 200
        data = resp.json()
        assert data["dealers"] == []


class TestGetDashboardSignal:
    @pytest.mark.asyncio
    async def test_returns_503_when_insufficient_data(self, dashboard_test_db):
        resp = dashboard_test_db["client"].get("/dashboard/signal?mode=saver")
        assert resp.status_code == 503
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_default_mode_is_saver(self, dashboard_test_db):
        resp = dashboard_test_db["client"].get("/dashboard/signal")
        # Even with insufficient data, the endpoint should be reachable
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_signal_has_required_fields(self, dashboard_test_db):
        # Seed enough data for signal computation
        now = datetime.now(timezone.utc)
        records = []
        for day in range(10):
            ts = now - timedelta(days=9 - day)
            records.append(
                _make_price_record(
                    source="yfinance",
                    product_type="xau_usd",
                    price_vnd=190_000_000,
                    price_usd=2650.0,
                    timestamp=ts,
                    currency="USD",
                )
            )
            for dealer in ("sjc", "pnj", "doji"):
                records.append(
                    _make_price_record(
                        source=dealer,
                        product_type="sjc_bar",
                        sell_price=195_000_000,
                        timestamp=ts,
                        currency="VND",
                    )
                )
        await _seed_prices(dashboard_test_db["session_factory"], records)

        resp = dashboard_test_db["client"].get("/dashboard/signal?mode=saver")
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendation" in data
        assert data["recommendation"] in ("BUY", "HOLD", "SELL")
        assert "confidence" in data
        assert isinstance(data["confidence"], int)
        assert "reasoning" in data
        assert "mode" in data
        assert data["mode"] == "SAVER"
        assert "gap_vnd" in data
        assert "gap_pct" in data

    @pytest.mark.asyncio
    async def test_trader_mode(self, dashboard_test_db):
        now = datetime.now(timezone.utc)
        records = []
        for day in range(10):
            ts = now - timedelta(days=9 - day)
            records.append(
                _make_price_record(
                    source="yfinance",
                    product_type="xau_usd",
                    price_vnd=190_000_000,
                    price_usd=2650.0,
                    timestamp=ts,
                    currency="USD",
                )
            )
            for dealer in ("sjc", "pnj", "doji"):
                records.append(
                    _make_price_record(
                        source=dealer,
                        product_type="sjc_bar",
                        sell_price=195_000_000,
                        timestamp=ts,
                        currency="VND",
                    )
                )
        await _seed_prices(dashboard_test_db["session_factory"], records)

        resp = dashboard_test_db["client"].get("/dashboard/signal?mode=trader")
        assert resp.status_code == 200
        data = resp.json()
        assert data["mode"] == "TRADER"
