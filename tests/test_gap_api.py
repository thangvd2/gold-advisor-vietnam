"""Tests for gap API endpoints."""

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
async def api_client(tmp_path):
    """Create TestClient with a temp SQLite database."""
    db_file = tmp_path / "test_api_gold.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield {
        "client": TestClient,
        "session_factory": session_factory,
        "db_file": str(db_file),
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


def _build_client(api_client, monkeypatch):
    """Build TestClient with DATABASE_URL pointing to temp file."""
    from unittest.mock import patch

    def get_settings(*args, **kwargs):
        from src.config import Settings

        return Settings(
            database_url=f"sqlite+aiosqlite:///{api_client['db_file']}",
        )

    with patch("src.api.routes.gap.get_settings", get_settings):
        from src.api.routes.gap import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/api/gap", tags=["gap"])
        return TestClient(app)


# ── Test 1: GET /api/gap/current returns 200 with gap data ────────────────────


class TestGetCurrentGap:
    @pytest.mark.asyncio
    async def test_returns_200_with_gap_data(self, api_client, monkeypatch):
        """Seed international + domestic → 200 with gap data."""
        now = datetime.now(timezone.utc)
        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=now,
            ),
            _make_record(
                source="sjc",
                product_type="sjc_bar",
                sell_price=195_000_000,
                timestamp=now,
                currency="VND",
            ),
            _make_record(
                source="pnj",
                product_type="sjc_bar",
                sell_price=196_000_000,
                timestamp=now,
                currency="VND",
            ),
        ]
        await _seed_records(api_client["session_factory"], records)

        client = _build_client(api_client, monkeypatch)
        resp = client.get("/api/gap/current")

        assert resp.status_code == 200
        data = resp.json()
        assert "gap" in data
        gap = data["gap"]
        assert "gap_vnd" in gap
        assert "gap_pct" in gap
        assert "avg_sjc_sell" in gap
        assert "intl_price_vnd" in gap
        assert "intl_price_usd" in gap
        assert "dealer_count" in gap
        assert "timestamp" in gap
        assert gap["dealer_count"] == 2

    @pytest.mark.asyncio
    async def test_returns_503_when_insufficient_data(self, api_client, monkeypatch):
        """Empty DB → 503 with error message."""
        client = _build_client(api_client, monkeypatch)
        resp = client.get("/api/gap/current")

        assert resp.status_code == 503
        data = resp.json()
        assert "error" in data


# ── Test 3-5: GET /api/gap/history ────────────────────────────────────────────


class TestGetGapHistory:
    @pytest.mark.asyncio
    async def test_returns_200_with_gap_array(self, api_client, monkeypatch):
        """Seed historical data → 200 with array of gaps."""
        now = datetime.now(timezone.utc)
        records: list[PriceRecord] = []

        for day in range(3):
            ts = now - timedelta(days=2 - day)
            records.append(
                _make_record(
                    source="yfinance",
                    product_type="xau_usd",
                    price_vnd=190_000_000,
                    price_usd=2650.0,
                    timestamp=ts,
                )
            )
            records.append(
                _make_record(
                    source="sjc",
                    product_type="sjc_bar",
                    sell_price=195_000_000,
                    timestamp=ts,
                    currency="VND",
                )
            )

        await _seed_records(api_client["session_factory"], records)

        client = _build_client(api_client, monkeypatch)
        resp = client.get("/api/gap/history?range=1W")

        assert resp.status_code == 200
        data = resp.json()
        assert data["range"] == "1W"
        assert isinstance(data["gaps"], list)
        assert len(data["gaps"]) > 0
        gap = data["gaps"][0]
        assert "timestamp" in gap
        assert "gap_vnd" in gap
        assert "gap_pct" in gap
        assert "ma_7d" in gap
        assert "ma_30d" in gap

    @pytest.mark.asyncio
    async def test_validates_range_parameter(self, api_client, monkeypatch):
        """range='invalid' → 422; valid ranges → 200."""
        now = datetime.now(timezone.utc)
        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=now,
            ),
            _make_record(
                source="sjc",
                product_type="sjc_bar",
                sell_price=195_000_000,
                timestamp=now,
                currency="VND",
            ),
        ]
        await _seed_records(api_client["session_factory"], records)

        client = _build_client(api_client, monkeypatch)
        resp = client.get("/api/gap/history?range=invalid")
        assert resp.status_code == 422

        for r in ["1W", "1M", "3M", "1Y"]:
            resp = client.get(f"/api/gap/history?range={r}")
            assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_returns_empty_array_when_no_data_in_range(
        self, api_client, monkeypatch
    ):
        """Only old data → 200 with empty gaps array."""
        now = datetime.now(timezone.utc)
        old_ts = now - timedelta(days=60)
        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=old_ts,
            ),
            _make_record(
                source="sjc",
                product_type="sjc_bar",
                sell_price=195_000_000,
                timestamp=old_ts,
                currency="VND",
            ),
        ]
        await _seed_records(api_client["session_factory"], records)

        client = _build_client(api_client, monkeypatch)
        resp = client.get("/api/gap/history?range=1W")

        assert resp.status_code == 200
        data = resp.json()
        assert data["range"] == "1W"
        assert data["gaps"] == []
