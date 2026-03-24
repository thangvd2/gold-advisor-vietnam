"""Tests for DuckDB gap calculation engine."""

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
    """Create a real SQLite file, seed it, return path for DuckDB to ATTACH."""
    db_file = tmp_path / "test_gold.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    # Create tables first, then yield session factory + path
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


# ── Test 1: calculate_current_gap with valid data ────────────────────────────


class TestCalculateCurrentGap:
    @pytest.mark.asyncio
    async def test_returns_correct_gap_vnd_and_pct(self, db_path):
        """1 intl (price_vnd=190M) + 3 domestic (sell=195M, 196M, 194M) → gap=5M, pct≈2.63%."""
        from src.analysis.gap import calculate_current_gap

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
            _make_record(
                source="doji",
                product_type="sjc_bar",
                sell_price=194_000_000,
                timestamp=now,
                currency="VND",
            ),
        ]
        await _seed_records(db_path["session_factory"], records)

        result = calculate_current_gap(db_path["path"])
        assert result is not None
        assert result["gap_vnd"] == pytest.approx(5_000_000, abs=1000)
        assert result["gap_pct"] == pytest.approx(2.63, abs=0.01)
        assert result["intl_price_vnd"] == pytest.approx(190_000_000, abs=1000)
        assert result["intl_price_usd"] == pytest.approx(2650.0, abs=1.0)
        assert result["dealer_count"] == 3

    @pytest.mark.asyncio
    async def test_averages_domestic_prices_across_dealers(self, db_path):
        """5 dealers with varying sell prices → avg_sjc_sell = mean."""
        from src.analysis.gap import calculate_current_gap

        now = datetime.now(timezone.utc)
        sell_prices = [195_000_000, 196_000_000, 194_000_000, 197_000_000, 193_000_000]
        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=now,
            ),
        ]
        for i, sp in enumerate(sell_prices):
            records.append(
                _make_record(
                    source=f"dealer_{i}",
                    product_type="sjc_bar",
                    sell_price=sp,
                    timestamp=now,
                    currency="VND",
                )
            )
        await _seed_records(db_path["session_factory"], records)

        result = calculate_current_gap(db_path["path"])
        assert result is not None
        expected_avg = sum(sell_prices) / len(sell_prices)
        assert result["avg_sjc_sell"] == pytest.approx(expected_avg, abs=1000)

    @pytest.mark.asyncio
    async def test_returns_none_when_no_international_price(self, db_path):
        """Only domestic records, no xau_usd → None."""
        from src.analysis.gap import calculate_current_gap

        now = datetime.now(timezone.utc)
        records = [
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
        await _seed_records(db_path["session_factory"], records)

        result = calculate_current_gap(db_path["path"])
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_domestic_prices(self, db_path):
        """Only xau_usd record, no sjc_bar → None."""
        from src.analysis.gap import calculate_current_gap

        now = datetime.now(timezone.utc)
        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=now,
            ),
        ]
        await _seed_records(db_path["session_factory"], records)

        result = calculate_current_gap(db_path["path"])
        assert result is None

    @pytest.mark.asyncio
    async def test_uses_price_vnd_for_international_not_sell_price(self, db_path):
        """xau_usd with sell_price=189M (prev close) and price_vnd=190M (current) → gap uses price_vnd."""
        from src.analysis.gap import calculate_current_gap

        now = datetime.now(timezone.utc)
        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                sell_price=189_000_000,
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
        await _seed_records(db_path["session_factory"], records)

        result = calculate_current_gap(db_path["path"])
        assert result is not None
        assert result["intl_price_vnd"] == pytest.approx(190_000_000, abs=1000)
        assert result["gap_vnd"] == pytest.approx(5_000_000, abs=1000)


# ── Test 6-8: calculate_historical_gaps ──────────────────────────────────────


class TestCalculateHistoricalGaps:
    @pytest.mark.asyncio
    async def test_returns_time_bucketed_gaps_with_moving_averages(self, db_path):
        """100 records over 14 days → 7d_ma populated after 7 days, 30d_ma always None."""
        from src.analysis.gap import calculate_historical_gaps

        now = datetime.now(timezone.utc)
        records: list[PriceRecord] = []

        for day in range(14):
            base_ts = now - timedelta(days=13 - day)
            for hour in range(0, 24, 2):
                ts = base_ts.replace(hour=hour, minute=0, second=0, microsecond=0)
                records.append(
                    _make_record(
                        source="yfinance",
                        product_type="xau_usd",
                        price_vnd=190_000_000 + day * 100_000,
                        price_usd=2650.0 + day * 1.5,
                        timestamp=ts,
                    )
                )
                records.append(
                    _make_record(
                        source="sjc",
                        product_type="sjc_bar",
                        sell_price=195_000_000 + day * 100_000,
                        timestamp=ts,
                        currency="VND",
                    )
                )

        await _seed_records(db_path["session_factory"], records)

        result = calculate_historical_gaps(db_path["path"], range="3M")
        assert len(result) > 0

        entries_with_7d_ma = [r for r in result if r["ma_7d"] is not None]
        assert len(entries_with_7d_ma) > 0

        entries_with_30d_ma = [r for r in result if r["ma_30d"] is not None]
        assert len(entries_with_30d_ma) == 0

    @pytest.mark.asyncio
    async def test_respects_range_parameter(self, db_path):
        """400 records over 1 year → range='1W' returns last 7 days only."""
        from src.analysis.gap import calculate_historical_gaps

        now = datetime.now(timezone.utc)
        records: list[PriceRecord] = []

        for day in range(365):
            base_ts = now - timedelta(days=364 - day)
            records.append(
                _make_record(
                    source="yfinance",
                    product_type="xau_usd",
                    price_vnd=190_000_000,
                    price_usd=2650.0,
                    timestamp=base_ts,
                )
            )
            records.append(
                _make_record(
                    source="sjc",
                    product_type="sjc_bar",
                    sell_price=195_000_000,
                    timestamp=base_ts,
                    currency="VND",
                )
            )

        await _seed_records(db_path["session_factory"], records)

        result_1w = calculate_historical_gaps(db_path["path"], range="1W")
        result_3m = calculate_historical_gaps(db_path["path"], range="3M")
        result_1y = calculate_historical_gaps(db_path["path"], range="1Y")

        assert len(result_1w) < len(result_3m) < len(result_1y)
        assert len(result_1w) <= 7 * 24 + 10

    @pytest.mark.asyncio
    async def test_handles_sparse_data_missing_buckets(self, db_path):
        """Domestic every 5 min, intl every 15 min → gaps only where both exist."""
        from src.analysis.gap import calculate_historical_gaps

        now = datetime.now(timezone.utc)
        records: list[PriceRecord] = []

        for minute in range(0, 180, 5):
            ts = now.replace(minute=minute, second=0, microsecond=0) - timedelta(
                hours=3
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

        for minute in range(0, 180, 15):
            ts = now.replace(minute=minute, second=0, microsecond=0) - timedelta(
                hours=3
            )
            records.append(
                _make_record(
                    source="yfinance",
                    product_type="xau_usd",
                    price_vnd=190_000_000,
                    price_usd=2650.0,
                    timestamp=ts,
                )
            )

        await _seed_records(db_path["session_factory"], records)

        result = calculate_historical_gaps(db_path["path"], range="1W")
        assert len(result) > 0

        entries_with_gap = [r for r in result if r["gap_vnd"] is not None]
        entries_without_gap = [r for r in result if r["gap_vnd"] is None]
        assert len(entries_with_gap) > 0
        assert len(entries_without_gap) > 0
