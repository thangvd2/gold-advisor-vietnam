"""Tests for signal API endpoints (Plan 04-03).

Uses TestClient with patched settings (same pattern as test_gap_api.py).
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

from src.engine.types import Recommendation, Signal, SignalFactor, SignalMode
from src.storage.models import Base, PriceRecord


@pytest_asyncio.fixture
async def signal_test_db(tmp_path):
    db_file = tmp_path / "test_signal_api.db"
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

    with patch("src.api.routes.signals.get_settings", mock_settings):
        from fastapi import FastAPI
        from src.api.routes.signals import router

        app = FastAPI()
        app.include_router(router, prefix="/api/signals", tags=["signals"])
        client = TestClient(app)

        yield {"client": client, "session_factory": session_factory}

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


async def _seed_gap_data(
    session_factory: async_sessionmaker[AsyncSession], days: int = 10
):
    now = datetime.now(timezone.utc)
    records = []
    for day in range(days):
        ts = now - timedelta(days=days - 1 - day)
        records.append(
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=ts,
            )
        )
        for dealer in ("sjc", "pnj", "doji"):
            records.append(
                _make_record(
                    source=dealer,
                    product_type="sjc_bar",
                    sell_price=195_000_000,
                    timestamp=ts,
                    currency="VND",
                )
            )
    await _seed_records(session_factory, records)


async def _seed_signal_record(
    session_factory: async_sessionmaker[AsyncSession], mode: str = "SAVER"
):
    from src.storage.repository import save_signal

    signal = Signal(
        recommendation=Recommendation.BUY,
        confidence=72,
        factors=[
            SignalFactor(name="gap", direction=0.5, weight=0.6, confidence=0.8),
        ],
        reasoning="Gap at 2.6% — favorable conditions for buying",
        mode=SignalMode(mode),
        timestamp=datetime.now(timezone.utc),
        gap_vnd=5_000_000,
        gap_pct=2.6,
    )
    async with session_factory() as session:
        await save_signal(session, signal)
        await session.commit()


class TestGetCurrentSignal:
    @pytest.mark.asyncio
    async def test_returns_200_with_signal_data(self, signal_test_db):
        await _seed_gap_data(signal_test_db["session_factory"])

        resp = signal_test_db["client"].get("/api/signals/current")

        assert resp.status_code == 200
        data = resp.json()
        assert "recommendation" in data
        assert data["recommendation"] in ("BUY", "HOLD", "SELL")
        assert "confidence" in data
        assert isinstance(data["confidence"], int)
        assert "reasoning" in data
        assert "mode" in data
        assert data["mode"] == "SAVER"
        assert "timestamp" in data
        assert "gap_vnd" in data
        assert "gap_pct" in data
        assert "factors" in data
        assert isinstance(data["factors"], list)

    @pytest.mark.asyncio
    async def test_returns_503_when_insufficient_data(self, signal_test_db):
        resp = signal_test_db["client"].get("/api/signals/current")
        assert resp.status_code == 503

    @pytest.mark.asyncio
    async def test_trader_mode_changes_signal(self, signal_test_db):
        await _seed_gap_data(signal_test_db["session_factory"])

        saver_resp = signal_test_db["client"].get("/api/signals/current?mode=saver")
        trader_resp = signal_test_db["client"].get("/api/signals/current?mode=trader")

        assert saver_resp.status_code == 200
        assert trader_resp.status_code == 200
        assert saver_resp.json()["mode"] == "SAVER"
        assert trader_resp.json()["mode"] == "TRADER"

    @pytest.mark.asyncio
    async def test_invalid_mode_returns_422(self, signal_test_db):
        resp = signal_test_db["client"].get("/api/signals/current?mode=invalid")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_factors_have_required_fields(self, signal_test_db):
        await _seed_gap_data(signal_test_db["session_factory"])

        resp = signal_test_db["client"].get("/api/signals/current")
        data = resp.json()

        for factor in data["factors"]:
            assert "name" in factor
            assert "direction" in factor
            assert "weight" in factor
            assert "confidence" in factor


class TestGetSignalHistory:
    @pytest.mark.asyncio
    async def test_returns_200_with_signal_list(self, signal_test_db):
        await _seed_signal_record(signal_test_db["session_factory"])

        resp = signal_test_db["client"].get("/api/signals/history?days=7")

        assert resp.status_code == 200
        data = resp.json()
        assert "signals" in data
        assert isinstance(data["signals"], list)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_signals(self, signal_test_db):
        resp = signal_test_db["client"].get("/api/signals/history?days=7")

        assert resp.status_code == 200
        data = resp.json()
        assert data["signals"] == []

    @pytest.mark.asyncio
    async def test_filters_by_mode(self, signal_test_db):
        await _seed_signal_record(signal_test_db["session_factory"], mode="SAVER")
        await _seed_signal_record(signal_test_db["session_factory"], mode="TRADER")

        saver_resp = signal_test_db["client"].get(
            "/api/signals/history?mode=saver&days=7"
        )
        trader_resp = signal_test_db["client"].get(
            "/api/signals/history?mode=trader&days=7"
        )

        assert saver_resp.status_code == 200
        assert trader_resp.status_code == 200

        saver_data = saver_resp.json()
        trader_data = trader_resp.json()

        for signal in saver_data["signals"]:
            assert signal["mode"] == "SAVER"
        for signal in trader_data["signals"]:
            assert signal["mode"] == "TRADER"
