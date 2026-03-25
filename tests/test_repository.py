"""Tests for FX rate fetcher and repository CRUD operations."""

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from src.ingestion.models import FetchedPrice
from src.ingestion.fetchers.vietcombank import VietcombankFxRateFetcher


# ── VietcombankFxRateFetcher tests ────────────────────────────────────────────


class TestVietcombankFxRateFetcher:
    @pytest.mark.asyncio
    async def test_fetch_returns_fx_rate(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "sellingRate": 25500.0,
            "buyingRate": 25400.0,
        }

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch(
            "src.ingestion.fetchers.vietcombank.httpx.AsyncClient",
            return_value=mock_client,
        ):
            fetcher = VietcombankFxRateFetcher()
            results = await fetcher.fetch()

        assert len(results) >= 1
        price = results[0]
        assert isinstance(price, FetchedPrice)
        assert price.source == "vietcombank"
        assert price.product_type == "usd_vnd"
        assert price.currency == "VND"
        assert price.sell_price is not None
        assert price.sell_price > 0

    @pytest.mark.asyncio
    async def test_fetch_handles_http_error(self):
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.json.return_value = {}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.ingestion.fetchers.vietcombank.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "src.ingestion.fetchers.vietcombank._fetch_yfinance_fallback",
                return_value=None,
            ),
        ):
            fetcher = VietcombankFxRateFetcher()
            results = await fetcher.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_handles_unexpected_format(self):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"unexpected_key": "unexpected_value"}

        mock_client = AsyncMock()
        mock_client.get.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.ingestion.fetchers.vietcombank.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "src.ingestion.fetchers.vietcombank._fetch_yfinance_fallback",
                return_value=None,
            ),
        ):
            fetcher = VietcombankFxRateFetcher()
            results = await fetcher.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_handles_network_failure(self):
        mock_client = AsyncMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with (
            patch(
                "src.ingestion.fetchers.vietcombank.httpx.AsyncClient",
                return_value=mock_client,
            ),
            patch(
                "src.ingestion.fetchers.vietcombank._fetch_yfinance_fallback",
                return_value=None,
            ),
        ):
            fetcher = VietcombankFxRateFetcher()
            results = await fetcher.fetch()

        assert results == []


# ── Repository tests ──────────────────────────────────────────────────────────


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


class TestRepository:
    @pytest.mark.asyncio
    async def test_save_price(self, db_session):
        from src.storage.repository import save_price

        fetched = FetchedPrice(
            source="yfinance",
            product_type="xau_usd",
            buy_price=2650.0,
            sell_price=2651.0,
            price_usd=2650.5,
            currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        record = await save_price(db_session, fetched)
        assert record.id is not None
        assert record.source == "yfinance"
        assert record.product_type == "xau_usd"
        assert record.buy_price == 2650.0
        assert record.price_usd == 2650.5
        assert record.validation_status == "valid"

    @pytest.mark.asyncio
    async def test_save_price_maps_all_fields(self, db_session):
        from src.storage.repository import save_price

        now = datetime.now(timezone.utc)
        fetched = FetchedPrice(
            source="vietcombank",
            product_type="usd_vnd",
            buy_price=25400.0,
            sell_price=25500.0,
            price_usd=None,
            price_vnd=25500.0,
            currency="VND",
            timestamp=now,
        )
        record = await save_price(db_session, fetched, validation_status="pending")
        assert record.id is not None
        assert record.source == "vietcombank"
        assert record.product_type == "usd_vnd"
        assert record.buy_price == 25400.0
        assert record.sell_price == 25500.0
        assert record.price_usd is None
        assert record.price_vnd == 25500.0
        assert record.currency == "VND"
        assert record.validation_status == "pending"

    @pytest.mark.asyncio
    async def test_get_latest_prices(self, db_session):
        from src.storage.repository import get_latest_prices, save_price

        now = datetime.now(timezone.utc)
        for i in range(3):
            fetched = FetchedPrice(
                source="yfinance",
                product_type="xau_usd",
                price_usd=2650.0 + i,
                currency="USD",
                timestamp=now - timedelta(hours=3 - i),
            )
            await save_price(db_session, fetched)

        latest = await get_latest_prices(
            db_session, source="yfinance", product_type="xau_usd"
        )
        assert len(latest) == 1
        assert latest[0].price_usd == 2652.0

    @pytest.mark.asyncio
    async def test_get_prices_since(self, db_session):
        from src.storage.repository import get_prices_since, save_price

        now = datetime.now(timezone.utc)
        for i in range(5):
            fetched = FetchedPrice(
                source="yfinance",
                product_type="xau_usd",
                price_usd=2650.0 + i,
                currency="USD",
                timestamp=now - timedelta(hours=5 - i),
            )
            await save_price(db_session, fetched)

        since = now - timedelta(hours=2)
        recent = await get_prices_since(db_session, since_dt=since)
        assert len(recent) == 2

    @pytest.mark.asyncio
    async def test_save_quality_alert(self, db_session):
        from src.storage.repository import save_quality_alert

        alert = await save_quality_alert(
            db_session,
            check_type="freshness",
            severity="warning",
            source="yfinance",
            message="No data received in 30 minutes",
        )
        assert alert.id is not None
        assert alert.check_type == "freshness"
        assert alert.severity == "warning"

    @pytest.mark.asyncio
    async def test_get_recent_alerts(self, db_session):
        from src.storage.repository import get_recent_alerts, save_quality_alert

        await save_quality_alert(
            db_session,
            check_type="anomaly",
            severity="critical",
            source="sjc",
            message="Price spike",
        )
        alerts = await get_recent_alerts(db_session, hours=24)
        assert len(alerts) == 1
        assert alerts[0].check_type == "anomaly"
