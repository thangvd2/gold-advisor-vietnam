"""Tests for data quality checks and normalizer pipeline."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock

from src.ingestion.models import FetchedPrice
from src.config import Settings


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_session():
    from sqlalchemy.ext.asyncio import (
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )

    from src.storage.models import Base

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


@pytest.fixture
def settings():
    return Settings(
        fetch_interval_minutes=5,
        freshness_threshold_minutes=15,
        anomaly_threshold_percent=10.0,
    )


def _make_fetched_price(
    source="yfinance",
    product_type="xau_usd",
    price_usd=2650.0,
    currency="USD",
    timestamp=None,
    fetched_at=None,
) -> FetchedPrice:
    now = datetime.now(timezone.utc)
    return FetchedPrice(
        source=source,
        product_type=product_type,
        buy_price=price_usd,
        sell_price=price_usd + 1.0,
        price_usd=price_usd,
        currency=currency,
        timestamp=timestamp or now,
        fetched_at=fetched_at or now,
    )


# ── Test 1: check_freshness flags stale records ───────────────────────────────


class TestCheckFreshness:
    @pytest.mark.asyncio
    async def test_flags_stale_record(self, db_session):
        """fetched_at older than threshold → returns warning alert."""
        from src.storage.repository import save_price
        from src.ingestion.quality import check_freshness

        stale_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        fetched = _make_fetched_price(fetched_at=stale_time)
        await save_price(db_session, fetched)

        alert = await check_freshness(
            db_session,
            source="yfinance",
            product_type="xau_usd",
            threshold_minutes=15,
        )
        assert alert is not None
        assert alert.severity == "warning"
        assert "stale" in alert.message.lower()
        assert alert.source == "yfinance"

    @pytest.mark.asyncio
    async def test_does_not_flag_fresh_record(self, db_session):
        """fetched_at within threshold → returns None."""
        from src.storage.repository import save_price
        from src.ingestion.quality import check_freshness

        fresh_time = datetime.now(timezone.utc) - timedelta(minutes=5)
        fetched = _make_fetched_price(fetched_at=fresh_time)
        await save_price(db_session, fetched)

        alert = await check_freshness(
            db_session,
            source="yfinance",
            product_type="xau_usd",
            threshold_minutes=15,
        )
        assert alert is None


# ── Test 3 & 4: check_anomaly flags price jumps ──────────────────────────────


class TestCheckAnomaly:
    @pytest.mark.asyncio
    async def test_flags_anomalous_price_jump(self, db_session):
        """Price change > threshold → returns warning alert."""
        from src.storage.repository import save_price
        from src.ingestion.quality import check_anomaly

        # Previous price: $2000
        old_fetched = _make_fetched_price(price_usd=2000.0)
        await save_price(db_session, old_fetched)

        # New price: $2250 (12.5% increase — above 10% threshold)
        new_fetched = _make_fetched_price(price_usd=2250.0)
        new_record = await save_price(db_session, new_fetched)

        alert = await check_anomaly(
            db_session,
            new_record=new_record,
            threshold_percent=10.0,
        )
        assert alert is not None
        assert alert.severity == "warning"
        assert alert.check_type == "anomaly"

    @pytest.mark.asyncio
    async def test_does_not_flag_normal_change(self, db_session):
        """Price change < threshold → returns None."""
        from src.storage.repository import save_price
        from src.ingestion.quality import check_anomaly

        # Previous price: $2650
        old_fetched = _make_fetched_price(price_usd=2650.0)
        await save_price(db_session, old_fetched)

        # New price: $2700 (~1.9% increase — well under 10%)
        new_fetched = _make_fetched_price(price_usd=2700.0)
        new_record = await save_price(db_session, new_fetched)

        alert = await check_anomaly(
            db_session,
            new_record=new_record,
            threshold_percent=10.0,
        )
        assert alert is None

    @pytest.mark.asyncio
    async def test_first_record_not_anomalous(self, db_session):
        """No previous record → not anomalous (first run)."""
        from src.storage.repository import save_price
        from src.ingestion.quality import check_anomaly

        new_fetched = _make_fetched_price(price_usd=2650.0)
        new_record = await save_price(db_session, new_fetched)

        alert = await check_anomaly(
            db_session,
            new_record=new_record,
            threshold_percent=10.0,
        )
        assert alert is None


# ── Test 5: check_missing for empty fetch ─────────────────────────────────────


class TestCheckMissing:
    @pytest.mark.asyncio
    async def test_missing_data_returns_critical_alert(self, db_session):
        """Empty fetch returns a critical severity alert."""
        from src.ingestion.quality import check_missing

        alert = await check_missing(
            db_session, source="yfinance", product_type="xau_usd"
        )
        assert alert is not None
        assert alert.severity == "critical"
        assert "missing" in alert.message.lower() or "no data" in alert.message.lower()
        assert alert.source == "yfinance"


# ── Test 6-8: fetch_and_store normalizer pipeline ─────────────────────────────


class TestFetchAndStore:
    @pytest.mark.asyncio
    async def test_pipeline_orchestrates_end_to_end(self, db_session, settings):
        """fetch → FX convert → save → quality check → return status."""
        from src.ingestion.normalizer import fetch_and_store

        gold_fetcher = AsyncMock()
        gold_fetcher.fetch.return_value = [
            _make_fetched_price(price_usd=2650.0, currency="USD"),
        ]

        fx_fetcher = AsyncMock()
        fx_fetcher.fetch.return_value = [
            FetchedPrice(
                source="vietcombank",
                product_type="usd_vnd",
                sell_price=25500.0,
                currency="VND",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        result = await fetch_and_store(db_session, gold_fetcher, fx_fetcher, settings)
        assert result["status"] == "ok"
        assert result["prices_saved"] == 1
        assert isinstance(result["alerts"], int)

    @pytest.mark.asyncio
    async def test_handles_empty_fetch_gracefully(self, db_session, settings):
        """Empty fetch → saves critical alert, returns failed status."""
        from src.ingestion.normalizer import fetch_and_store
        from src.storage.repository import get_recent_alerts

        gold_fetcher = AsyncMock()
        gold_fetcher.fetch.return_value = []

        fx_fetcher = AsyncMock()

        result = await fetch_and_store(db_session, gold_fetcher, fx_fetcher, settings)
        assert result["status"] == "failed"
        assert result["alerts"] == 1

        alerts = await get_recent_alerts(db_session, hours=24)
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_updates_validation_status_on_anomaly(self, db_session, settings):
        """When quality check detects anomaly, PriceRecord validation_status updated."""
        from src.ingestion.normalizer import fetch_and_store
        from src.storage.repository import get_latest_prices, save_price

        # Insert a previous record with a much lower price
        old_fetched = _make_fetched_price(price_usd=2000.0)
        await save_price(db_session, old_fetched)
        await db_session.commit()

        # Now fetch a new record with price 50% higher (clearly anomalous)
        gold_fetcher = AsyncMock()
        gold_fetcher.fetch.return_value = [
            _make_fetched_price(price_usd=3000.0, currency="USD"),
        ]

        fx_fetcher = AsyncMock()
        fx_fetcher.fetch.return_value = [
            FetchedPrice(
                source="vietcombank",
                product_type="usd_vnd",
                sell_price=25500.0,
                currency="VND",
                timestamp=datetime.now(timezone.utc),
            )
        ]

        result = await fetch_and_store(db_session, gold_fetcher, fx_fetcher, settings)
        assert result["status"] == "ok"

        latest = await get_latest_prices(
            db_session, source="yfinance", product_type="xau_usd"
        )
        # The latest record should have its validation_status updated to "warning"
        anomalous_records = [r for r in latest if r.validation_status == "warning"]
        assert len(anomalous_records) >= 1

    @pytest.mark.asyncio
    async def test_handles_fetcher_exception_gracefully(self, db_session, settings):
        """Fetcher raises exception → saves alert, doesn't crash."""
        from src.ingestion.normalizer import fetch_and_store
        from src.storage.repository import get_recent_alerts

        gold_fetcher = AsyncMock()
        gold_fetcher.fetch.side_effect = Exception("Network timeout")

        fx_fetcher = AsyncMock()

        result = await fetch_and_store(db_session, gold_fetcher, fx_fetcher, settings)
        assert result["status"] == "failed"

        alerts = await get_recent_alerts(db_session, hours=24)
        assert len(alerts) >= 1
        assert alerts[0].severity == "critical"
