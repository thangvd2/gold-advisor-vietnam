"""Tests for signal persistence — SignalRecord model and repository CRUD."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.engine.types import Recommendation, Signal, SignalFactor, SignalMode
from src.storage.models import Base


@pytest_asyncio.fixture
async def db_session(tmp_path):
    db_file = tmp_path / "test_signal.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with session_factory() as session:
        yield session

    await engine.dispose()


def _make_signal(
    recommendation: Recommendation = Recommendation.BUY,
    confidence: int = 72,
    mode: SignalMode = SignalMode.SAVER,
    gap_pct: float | None = 2.8,
    gap_vnd: float | None = 5_000_000,
) -> Signal:
    return Signal(
        recommendation=recommendation,
        confidence=confidence,
        factors=[
            SignalFactor(name="gap", direction=0.5, weight=0.6, confidence=0.8),
            SignalFactor(name="trend", direction=0.3, weight=0.4, confidence=0.7),
        ],
        reasoning="Gap at 2.8% vs 30-day avg 4.5% — favorable conditions observed for buying",
        mode=mode,
        timestamp=datetime(2026, 3, 24, 12, 0, 0),
        gap_vnd=gap_vnd,
        gap_pct=gap_pct,
    )


class TestSaveSignal:
    @pytest.mark.asyncio
    async def test_save_signal_returns_record_with_id(self, db_session):
        """save_signal persists a Signal and returns SignalRecord with populated id."""
        from src.storage.repository import save_signal

        signal = _make_signal()
        record = await save_signal(db_session, signal)

        assert record.id is not None
        assert record.recommendation == "BUY"
        assert record.confidence == 72
        assert record.gap_pct == 2.8
        assert record.gap_vnd == 5_000_000
        assert record.mode == "SAVER"

    @pytest.mark.asyncio
    async def test_factor_data_serialized_as_json(self, db_session):
        """factor_data stores all factor names, directions, weights as JSON."""
        import json

        from src.storage.repository import save_signal

        signal = _make_signal()
        record = await save_signal(db_session, signal)

        factors = json.loads(record.factor_data)
        assert len(factors) == 2
        assert factors[0]["name"] == "gap"
        assert factors[0]["direction"] == 0.5
        assert factors[0]["weight"] == 0.6
        assert factors[0]["confidence"] == 0.8

    @pytest.mark.asyncio
    async def test_created_at_auto_populated_utc(self, db_session):
        """created_at is auto-populated with a UTC timestamp."""
        from src.storage.repository import save_signal

        signal = _make_signal()
        before = datetime.now(timezone.utc) - timedelta(seconds=1)
        record = await save_signal(db_session, signal)
        after = datetime.now(timezone.utc) + timedelta(seconds=1)

        assert record.created_at.tzinfo is not None
        assert before <= record.created_at <= after


class TestGetLatestSignal:
    @pytest.mark.asyncio
    async def test_returns_most_recent_signal(self, db_session):
        """get_latest_signal returns the most recent signal by created_at."""
        from src.storage.repository import get_latest_signal, save_signal

        signal1 = _make_signal(mode=SignalMode.SAVER, confidence=60, gap_pct=3.0)
        signal1.timestamp = datetime(2026, 3, 24, 10, 0, 0)
        await save_signal(db_session, signal1)
        await db_session.commit()

        signal2 = _make_signal(mode=SignalMode.SAVER, confidence=80, gap_pct=2.0)
        signal2.timestamp = datetime(2026, 3, 24, 12, 0, 0)
        await save_signal(db_session, signal2)
        await db_session.commit()

        latest = await get_latest_signal(db_session, mode=SignalMode.SAVER)
        assert latest is not None
        assert latest.confidence == 80
        assert latest.gap_pct == 2.0

    @pytest.mark.asyncio
    async def test_returns_none_when_no_signals_exist(self, db_session):
        """get_latest_signal returns None when table is empty."""
        from src.storage.repository import get_latest_signal

        result = await get_latest_signal(db_session, mode=SignalMode.SAVER)
        assert result is None

    @pytest.mark.asyncio
    async def test_filters_by_mode(self, db_session):
        """get_latest_signal with mode returns only signals for that mode."""
        from src.storage.repository import get_latest_signal, save_signal

        saver_signal = _make_signal(mode=SignalMode.SAVER, confidence=50)
        saver_signal.timestamp = datetime(2026, 3, 24, 12, 0, 0)
        await save_signal(db_session, saver_signal)
        await db_session.commit()

        trader_signal = _make_signal(mode=SignalMode.TRADER, confidence=90)
        trader_signal.timestamp = datetime(2026, 3, 24, 13, 0, 0)
        await save_signal(db_session, trader_signal)
        await db_session.commit()

        latest_saver = await get_latest_signal(db_session, mode=SignalMode.SAVER)
        latest_trader = await get_latest_signal(db_session, mode=SignalMode.TRADER)

        assert latest_saver.confidence == 50
        assert latest_trader.confidence == 90

    @pytest.mark.asyncio
    async def test_mode_none_returns_any_mode(self, db_session):
        """get_latest_signal with mode=None returns latest regardless of mode."""
        from src.storage.repository import get_latest_signal, save_signal

        saver_signal = _make_signal(mode=SignalMode.SAVER, confidence=50)
        saver_signal.timestamp = datetime(2026, 3, 24, 12, 0, 0)
        await save_signal(db_session, saver_signal)
        await db_session.commit()

        trader_signal = _make_signal(mode=SignalMode.TRADER, confidence=90)
        trader_signal.timestamp = datetime(2026, 3, 24, 13, 0, 0)
        await save_signal(db_session, trader_signal)
        await db_session.commit()

        latest = await get_latest_signal(db_session, mode=None)
        assert latest.confidence == 90


class TestGetSignalsSince:
    @pytest.mark.asyncio
    async def test_returns_signals_after_datetime(self, db_session):
        """get_signals_since returns only signals created after since_dt."""
        from src.storage.repository import get_signals_since, save_signal

        signal1 = _make_signal(mode=SignalMode.SAVER, confidence=50)
        signal1.timestamp = datetime(2026, 3, 24, 10, 0, 0)
        await save_signal(db_session, signal1)
        await db_session.commit()

        since_dt = datetime.now(timezone.utc) - timedelta(seconds=30)

        signal2 = _make_signal(mode=SignalMode.SAVER, confidence=80)
        signal2.timestamp = datetime(2026, 3, 24, 12, 0, 0)
        await save_signal(db_session, signal2)
        await db_session.commit()

        signals = await get_signals_since(db_session, since_dt, mode=SignalMode.SAVER)
        assert len(signals) >= 1
        assert any(s.confidence == 80 for s in signals)

    @pytest.mark.asyncio
    async def test_filters_by_mode(self, db_session):
        """get_signals_since with mode returns only signals for that mode."""
        from src.storage.repository import get_signals_since, save_signal

        since_dt = datetime(2026, 3, 23, 0, 0, 0, tzinfo=timezone.utc)

        saver_signal = _make_signal(mode=SignalMode.SAVER, confidence=50)
        await save_signal(db_session, saver_signal)
        await db_session.commit()

        trader_signal = _make_signal(mode=SignalMode.TRADER, confidence=90)
        await save_signal(db_session, trader_signal)
        await db_session.commit()

        saver_signals = await get_signals_since(
            db_session, since_dt, mode=SignalMode.SAVER
        )
        assert len(saver_signals) == 1
        assert saver_signals[0].mode == "SAVER"
