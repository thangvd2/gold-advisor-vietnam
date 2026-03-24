"""Tests for price chart API endpoints."""

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


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def price_test_db(tmp_path):
    """Create temp SQLite DB, return TestClient with patched settings."""
    db_file = tmp_path / "test_price_api.db"
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

    with patch("src.api.routes.prices.get_settings", mock_settings):
        from src.api.routes.prices import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/prices", tags=["prices"])
        client = TestClient(app)

        yield {
            "client": client,
            "session_factory": session_factory,
        }

    await engine.dispose()


def _make_record(
    source: str,
    product_type: str,
    sell_price: float | None = None,
    price_vnd: float | None = None,
    price_usd: float | None = None,
    timestamp: datetime | None = None,
    currency: str = "USD",
) -> PriceRecord:
    return PriceRecord(
        source=source,
        product_type=product_type,
        buy_price=sell_price,
        sell_price=sell_price,
        price_usd=price_usd,
        price_vnd=price_vnd,
        currency=currency,
        timestamp=timestamp or datetime.now(timezone.utc),
        fetched_at=datetime.now(timezone.utc),
        validation_status="valid",
    )


async def _seed_records(
    session_factory: async_sessionmaker[AsyncSession],
    records: list[PriceRecord],
) -> None:
    async with session_factory() as session:
        session.add_all(records)
        await session.commit()


# ── Test 1: GET /api/prices/history returns 200 with price data ──────────────


class TestGetPriceHistory:
    @pytest.mark.asyncio
    async def test_returns_200_with_sjc_bar_price_data(self, price_test_db):
        """Seed SJC bar records → 200 with price data."""
        now = datetime.now(timezone.utc)
        base = now - timedelta(hours=3)
        base = base.replace(second=0, microsecond=0)
        records: list[PriceRecord] = []

        for minute in range(0, 180, 5):
            ts = base + timedelta(minutes=minute)
            records.append(
                _make_record(
                    source="sjc",
                    product_type="sjc_bar",
                    sell_price=195_000_000,
                    timestamp=ts,
                    currency="VND",
                )
            )

        await _seed_records(price_test_db["session_factory"], records)

        resp = price_test_db["client"].get(
            "/api/prices/history?product_type=sjc_bar&range=1D"
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["product_type"] == "sjc_bar"
        assert data["range"] == "1D"
        assert isinstance(data["prices"], list)
        assert len(data["prices"]) > 0
        point = data["prices"][0]
        assert "x" in point
        assert "y" in point

    @pytest.mark.asyncio
    async def test_returns_xau_usd_international_prices(self, price_test_db):
        """Seed xau_usd records with price_vnd → prices array with y=price_vnd."""
        now = datetime.now(timezone.utc)
        base = now - timedelta(hours=2)
        base = base.replace(second=0, microsecond=0)
        records: list[PriceRecord] = []

        for minute in range(0, 120, 10):
            ts = base + timedelta(minutes=minute)
            records.append(
                _make_record(
                    source="yfinance",
                    product_type="xau_usd",
                    sell_price=189_500_000,
                    price_vnd=190_000_000,
                    price_usd=2650.0,
                    timestamp=ts,
                )
            )

        await _seed_records(price_test_db["session_factory"], records)

        resp = price_test_db["client"].get(
            "/api/prices/history?product_type=xau_usd&range=1D"
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["product_type"] == "xau_usd"
        assert len(data["prices"]) > 0
        assert data["prices"][0]["y"] == pytest.approx(190_000_000, abs=1000)

    @pytest.mark.asyncio
    async def test_validates_product_type_parameter(self, price_test_db):
        """product_type='invalid' → 422; valid values → 200."""
        resp = price_test_db["client"].get(
            "/api/prices/history?product_type=invalid&range=1D"
        )
        assert resp.status_code == 422

        for pt in ["sjc_bar", "ring_gold", "xau_usd"]:
            resp = price_test_db["client"].get(
                f"/api/prices/history?product_type={pt}&range=1D"
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_validates_range_parameter(self, price_test_db):
        """range='invalid' → 422; valid values → 200."""
        resp = price_test_db["client"].get(
            "/api/prices/history?product_type=sjc_bar&range=invalid"
        )
        assert resp.status_code == 422

        for r in ["1D", "1W", "1M", "1Y"]:
            resp = price_test_db["client"].get(
                f"/api/prices/history?product_type=sjc_bar&range={r}"
            )
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_empty_prices_when_no_data_in_range(self, price_test_db):
        """Empty DB → 200 with empty prices array."""
        resp = price_test_db["client"].get(
            "/api/prices/history?product_type=sjc_bar&range=1D"
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["product_type"] == "sjc_bar"
        assert data["range"] == "1D"
        assert data["prices"] == []

    @pytest.mark.asyncio
    async def test_defaults_to_range_1m(self, price_test_db):
        """No range query param → uses 1M range."""
        now = datetime.now(timezone.utc)
        old_ts = now - timedelta(days=60)
        records = [
            _make_record(
                source="sjc",
                product_type="sjc_bar",
                sell_price=195_000_000,
                timestamp=now,
                currency="VND",
            ),
        ]
        await _seed_records(price_test_db["session_factory"], records)

        resp = price_test_db["client"].get("/api/prices/history?product_type=sjc_bar")

        assert resp.status_code == 200
        data = resp.json()
        assert data["range"] == "1M"
