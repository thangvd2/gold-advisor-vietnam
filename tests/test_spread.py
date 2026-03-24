"""Tests for buy/sell spread calculation on price save."""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.ingestion.models import FetchedPrice
from src.storage.models import Base


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session

    await engine.dispose()


class TestSpreadCalculation:
    @pytest.mark.asyncio
    async def test_spread_with_both_buy_and_sell(self, db_session):
        """Test 6: save_price with both buy and sell → record.spread == sell - buy."""
        from src.storage.repository import save_price

        fetched = FetchedPrice(
            source="btmc",
            product_type="sjc_bar",
            buy_price=167200000.0,
            sell_price=170200000.0,
            currency="VND",
            timestamp=datetime.now(timezone.utc),
        )
        record = await save_price(db_session, fetched)
        assert record.spread is not None
        assert record.spread == 3000000.0

    @pytest.mark.asyncio
    async def test_spread_with_only_sell(self, db_session):
        """Test 7: save_price with only sell → record.spread is None."""
        from src.storage.repository import save_price

        fetched = FetchedPrice(
            source="btmc",
            product_type="ring_gold",
            buy_price=None,
            sell_price=170200000.0,
            currency="VND",
            timestamp=datetime.now(timezone.utc),
        )
        record = await save_price(db_session, fetched)
        assert record.spread is None

    @pytest.mark.asyncio
    async def test_spread_with_only_buy(self, db_session):
        """Test 8: save_price with only buy → record.spread is None."""
        from src.storage.repository import save_price

        fetched = FetchedPrice(
            source="btmc",
            product_type="sjc_bar",
            buy_price=167200000.0,
            sell_price=None,
            currency="VND",
            timestamp=datetime.now(timezone.utc),
        )
        record = await save_price(db_session, fetched)
        assert record.spread is None

    @pytest.mark.asyncio
    async def test_spread_with_neither(self, db_session):
        """Test 9: save_price with neither → record.spread is None."""
        from src.storage.repository import save_price

        fetched = FetchedPrice(
            source="btmc",
            product_type="sjc_bar",
            buy_price=None,
            sell_price=None,
            currency="VND",
            timestamp=datetime.now(timezone.utc),
        )
        record = await save_price(db_session, fetched)
        assert record.spread is None

    @pytest.mark.asyncio
    async def test_get_latest_prices_returns_spread(self, db_session):
        """Test 10: get_latest_prices returns records with spread populated."""
        from src.storage.repository import get_latest_prices, save_price

        now = datetime.now(timezone.utc)
        fetched = FetchedPrice(
            source="btmc",
            product_type="sjc_bar",
            buy_price=167200000.0,
            sell_price=170200000.0,
            currency="VND",
            timestamp=now,
        )
        await save_price(db_session, fetched)

        latest = await get_latest_prices(
            db_session, source="btmc", product_type="sjc_bar"
        )
        assert len(latest) == 1
        assert latest[0].spread == 3000000.0
