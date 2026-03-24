from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.storage.models import Base, PriceRecord, PolicyEvent


@pytest_asyncio.fixture
async def db_path(tmp_path):
    db_file = tmp_path / "test_pipeline_seasonal_policy.db"
    db_url = f"sqlite+aiosqlite:///{db_file}"

    engine = create_async_engine(db_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    yield {"session_factory": session_factory, "path": str(db_file)}

    await engine.dispose()


async def _seed_full_gap_data(
    session_factory: async_sessionmaker[AsyncSession],
    days: int = 10,
) -> None:
    now = datetime.now(timezone.utc)
    records = []
    for day in range(days):
        ts = now - timedelta(days=days - 1 - day)
        records.append(
            PriceRecord(
                source="yfinance",
                product_type="xau_usd",
                price_vnd=190_000_000,
                price_usd=2650.0,
                timestamp=ts,
                currency="USD",
                fetched_at=ts,
                validation_status="valid",
            )
        )
        for dealer in ("sjc", "pnj", "doji"):
            records.append(
                PriceRecord(
                    source=dealer,
                    product_type="sjc_bar",
                    buy_price=194_800_000,
                    sell_price=195_000_000,
                    timestamp=ts,
                    currency="VND",
                    fetched_at=ts,
                    validation_status="valid",
                )
            )
    async with session_factory() as session:
        session.add_all(records)
        await session.commit()


async def _add_policy_event(
    session_factory: async_sessionmaker[AsyncSession],
    severity: str = "high",
    impact: str = "bearish",
):
    async with session_factory() as session:
        session.add(
            PolicyEvent(
                event_type="auction",
                description="SBV gold auction",
                impact=impact,
                severity=severity,
                effective_date=datetime.now(timezone.utc),
                is_active=True,
            )
        )
        await session.commit()


class TestPipelineSeasonalIntegration:
    @pytest.mark.asyncio
    async def test_seasonal_factor_in_signal(self, db_path):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        signal = compute_signal(db_path["path"])

        factor_names = {f.name for f in signal.factors}
        assert "seasonal" in factor_names

    @pytest.mark.asyncio
    async def test_seasonal_factor_has_zero_direction(self, db_path):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        signal = compute_signal(db_path["path"])

        seasonal_factor = next(
            (f for f in signal.factors if f.name == "seasonal"), None
        )
        assert seasonal_factor is not None
        assert seasonal_factor.direction == 0.0

    @pytest.mark.asyncio
    async def test_high_demand_season_reduces_confidence(self, db_path, monkeypatch):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])

        monkeypatch.setattr("src.engine.pipeline._current_month", lambda: 1)

        signal = compute_signal(db_path["path"])

        seasonal_factor = next(
            (f for f in signal.factors if f.name == "seasonal"), None
        )
        assert seasonal_factor is not None
        assert seasonal_factor.confidence == 0.7

    @pytest.mark.asyncio
    async def test_low_demand_season_no_modifier(self, db_path, monkeypatch):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])

        monkeypatch.setattr("src.engine.pipeline._current_month", lambda: 5)

        signal = compute_signal(db_path["path"])

        seasonal_factor = next(
            (f for f in signal.factors if f.name == "seasonal"), None
        )
        assert seasonal_factor is not None
        assert seasonal_factor.confidence == 1.0


class TestPipelinePolicyIntegration:
    @pytest.mark.asyncio
    async def test_policy_override_caps_confidence(self, db_path):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        await _add_policy_event(db_path["session_factory"], severity="high")

        signal = compute_signal(db_path["path"])

        assert signal.confidence <= 30

    @pytest.mark.asyncio
    async def test_no_policy_event_normal_confidence(self, db_path):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])

        signal = compute_signal(db_path["path"])

        assert signal.confidence > 0
        assert signal.confidence <= 100


class TestPipelineReasoningIntegration:
    @pytest.mark.asyncio
    async def test_reasoning_includes_seasonal_context(self, db_path, monkeypatch):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])

        monkeypatch.setattr("src.engine.pipeline._current_month", lambda: 1)

        signal = compute_signal(db_path["path"])

        assert signal.reasoning is not None
        assert len(signal.reasoning) > 0

    @pytest.mark.asyncio
    async def test_reasoning_includes_policy_alert(self, db_path):
        from src.engine.pipeline import compute_signal

        await _seed_full_gap_data(db_path["session_factory"])
        await _add_policy_event(db_path["session_factory"], severity="high")

        signal = compute_signal(db_path["path"])

        assert (
            "policy" in signal.reasoning.lower()
            or "state bank" in signal.reasoning.lower()
        )
