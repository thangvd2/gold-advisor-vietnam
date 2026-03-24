"""Tests for signal pipeline orchestrator (Plan 04-03).

Pipeline wires: gap data → factors (gap, spread, trend) → composite → reasoning → Signal.
Uses real SQLite + DuckDB (same pattern as test_gap.py).
"""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.storage.models import Base, PriceRecord


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def db_path(tmp_path):
    """Create a real SQLite file with tables, seed data, return path."""
    db_file = tmp_path / "test_pipeline.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield {"session_factory": session_factory, "path": str(db_file)}

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


async def _seed_full_gap_data(
    session_factory: async_sessionmaker[AsyncSession],
    days: int = 10,
) -> None:
    """Seed enough data for gap calculation with historical context."""
    now = datetime.now(timezone.utc)
    records = []
    for day in range(days):
        ts = now - timedelta(days=days - 1 - day)
        # International price
        records.append(
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=ts,
            )
        )
        # Domestic prices from multiple dealers
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


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestComputeSignal:
    @pytest.mark.asyncio
    async def test_returns_valid_signal_with_all_fields(self, db_path):
        """Pipeline produces Signal with recommendation, confidence, reasoning populated."""
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        signal = compute_signal(db_path["path"])

        assert signal.recommendation in ("BUY", "HOLD", "SELL")
        assert isinstance(signal.confidence, int)
        assert 0 <= signal.confidence <= 100
        assert isinstance(signal.reasoning, str)
        assert len(signal.reasoning) > 0
        assert signal.mode == "SAVER"  # default mode
        assert signal.gap_vnd is not None
        assert signal.gap_pct is not None
        assert signal.timestamp is not None

    @pytest.mark.asyncio
    async def test_returns_hold_with_zero_confidence_when_no_data(self, db_path):
        """Empty database → HOLD with confidence=0."""
        from src.engine.pipeline import compute_signal

        signal = compute_signal(db_path["path"])

        assert signal.recommendation == "HOLD"
        assert signal.confidence == 0
        assert signal.factors == []
        assert "Insufficient data" in signal.reasoning

    @pytest.mark.asyncio
    async def test_factors_contain_gap_spread_and_trend(self, db_path):
        """Pipeline computes all three signal factors."""
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        signal = compute_signal(db_path["path"])

        factor_names = {f.name for f in signal.factors}
        assert "gap" in factor_names
        assert "spread" in factor_names
        assert "trend" in factor_names

    @pytest.mark.asyncio
    async def test_trader_mode_changes_thresholds(self, db_path):
        """TRADER mode uses trader-specific thresholds."""
        from src.engine.pipeline import compute_signal
        from src.engine.types import SignalMode

        await _seed_full_gap_data(db_path["session_factory"])

        saver_signal = compute_signal(db_path["path"], mode=SignalMode.SAVER)
        trader_signal = compute_signal(db_path["path"], mode=SignalMode.TRADER)

        assert saver_signal.mode == SignalMode.SAVER
        assert trader_signal.mode == SignalMode.TRADER

    @pytest.mark.asyncio
    async def test_gap_vnd_and_pct_populated_from_data(self, db_path):
        """Signal gap_vnd and gap_pct come from actual gap calculation."""
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        signal = compute_signal(db_path["path"])

        # With intl=190M and domestic=195M, gap should be ~5M VND and ~2.63%
        assert signal.gap_vnd is not None
        assert signal.gap_pct is not None
        assert signal.gap_vnd > 0
        assert signal.gap_pct > 0
