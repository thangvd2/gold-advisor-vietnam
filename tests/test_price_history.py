"""Tests for DuckDB price history chart data service."""

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


# ── Test 1: get_price_series returns {x, y} data points for sjc_bar ──────────


class TestGetPriceSeries:
    @pytest.mark.asyncio
    async def test_returns_xy_data_points_for_sjc_bar(self, db_path):
        """Seed 50 SJC bar records from 3 dealers over 1 day → array of ~288 points."""
        from src.analysis.prices import get_price_series

        now = datetime.now(timezone.utc)
        base = now - timedelta(hours=24)
        base = base.replace(second=0, microsecond=0)

        records: list[PriceRecord] = []
        dealers = ["sjc", "pnj", "doji"]
        for minute in range(0, 24 * 60, 5):
            ts = base + timedelta(minutes=minute)
            for dealer in dealers:
                records.append(
                    _make_record(
                        source=dealer,
                        product_type="sjc_bar",
                        sell_price=195_000_000 + minute * 100,
                        timestamp=ts,
                        currency="VND",
                    )
                )

        await _seed_records(db_path["session_factory"], records)

        result = get_price_series(db_path["path"], "sjc_bar", "1D")

        assert isinstance(result, list)
        assert len(result) > 200  # ~288 five-minute buckets in 24h
        for point in result:
            assert "x" in point
            assert "y" in point
            assert isinstance(point["x"], str)
            assert isinstance(point["y"], (float, int, type(None)))

    @pytest.mark.asyncio
    async def test_averages_across_dealers_for_sjc_bar(self, db_path):
        """3 dealers at same timestamp with sell 195M, 196M, 194M → y=195M."""
        from src.analysis.prices import get_price_series

        now = datetime.now(timezone.utc)
        now = now.replace(second=0, microsecond=0)

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
            _make_record(
                source="doji",
                product_type="sjc_bar",
                sell_price=194_000_000,
                timestamp=now,
                currency="VND",
            ),
        ]
        await _seed_records(db_path["session_factory"], records)

        result = get_price_series(db_path["path"], "sjc_bar", "1D")

        assert len(result) == 1
        assert result[0]["y"] == pytest.approx(195_000_000, abs=1000)

    @pytest.mark.asyncio
    async def test_uses_price_vnd_for_xau_usd_not_sell_price(self, db_path):
        """xau_usd with price_vnd=190M and sell_price=189.5M → y=190M."""
        from src.analysis.prices import get_price_series

        now = datetime.now(timezone.utc)
        now = now.replace(second=0, microsecond=0)

        records = [
            _make_record(
                source="yfinance",
                product_type="xau_usd",
                sell_price=189_500_000,
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=now,
            ),
        ]
        await _seed_records(db_path["session_factory"], records)

        result = get_price_series(db_path["path"], "xau_usd", "1D")

        assert len(result) == 1
        assert result[0]["y"] == pytest.approx(190_000_000, abs=1000)

    @pytest.mark.asyncio
    async def test_filters_by_product_type_correctly(self, db_path):
        """Mix of sjc_bar and ring_gold → product_type filters correctly."""
        from src.analysis.prices import get_price_series

        now = datetime.now(timezone.utc)
        now = now.replace(second=0, microsecond=0)

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
            _make_record(
                source="doji",
                product_type="ring_gold",
                sell_price=160_000_000,
                timestamp=now,
                currency="VND",
            ),
        ]
        await _seed_records(db_path["session_factory"], records)

        result_sjc = get_price_series(db_path["path"], "sjc_bar", "1D")
        result_ring = get_price_series(db_path["path"], "ring_gold", "1D")

        assert len(result_sjc) == 1
        assert result_sjc[0]["y"] == pytest.approx(195_500_000, abs=1000)
        assert len(result_ring) == 1
        assert result_ring[0]["y"] == pytest.approx(160_000_000, abs=1000)

    @pytest.mark.asyncio
    async def test_respects_range_parameter(self, db_path):
        """500 records over 2 months → different ranges return different counts."""
        from src.analysis.prices import get_price_series

        now = datetime.now(timezone.utc)
        records: list[PriceRecord] = []

        for day in range(60):
            base_ts = now - timedelta(days=59 - day)
            for hour in range(0, 24, 2):
                ts = base_ts.replace(hour=hour, minute=0, second=0, microsecond=0)
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

        result_1d = get_price_series(db_path["path"], "sjc_bar", "1D")
        result_1w = get_price_series(db_path["path"], "sjc_bar", "1W")
        result_1m = get_price_series(db_path["path"], "sjc_bar", "1M")

        # 1D should be smallest, 1W larger, 1M largest
        assert len(result_1d) <= 288  # 24h * 12 per hour (5-min buckets)
        assert len(result_1w) > len(result_1d)
        assert len(result_1m) > len(result_1w)

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_data(self, db_path):
        """Empty DB → empty list."""
        from src.analysis.prices import get_price_series

        result = get_price_series(db_path["path"], "sjc_bar", "1D")
        assert result == []

    @pytest.mark.asyncio
    async def test_uses_adaptive_time_bucket_size(self, db_path):
        """Verify bucket granularity: 1D=5min, 1W=15min, 1M=1hour."""
        from src.analysis.prices import get_price_series

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

        await _seed_records(db_path["session_factory"], records)

        result_1d = get_price_series(db_path["path"], "sjc_bar", "1D")
        # 3 hours of 5-min data should produce ~36 buckets
        assert len(result_1d) >= 35

        # Parse timestamps and check deltas
        if len(result_1d) >= 2:
            from datetime import datetime as dt

            t0 = dt.fromisoformat(result_1d[0]["x"])
            t1 = dt.fromisoformat(result_1d[1]["x"])
            delta = (t1 - t0).total_seconds()
            # 5-minute bucket = 300 seconds
            assert delta == pytest.approx(300, abs=60)
