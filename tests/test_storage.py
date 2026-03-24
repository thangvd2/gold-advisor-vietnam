"""Tests for config, database models, and database initialization."""

from datetime import datetime, timezone

import pytest

from src.config import Settings
from src.storage.database import async_session, init_db
from src.storage.models import DataQualityAlert, PriceRecord


class TestSettings:
    def test_default_settings(self):
        settings = Settings()
        assert settings.app_name == "gold_advisor"
        assert settings.database_url == "sqlite+aiosqlite:///./gold_advisor.db"
        assert settings.log_level == "INFO"
        assert settings.fetch_interval_minutes == 5
        assert settings.freshness_threshold_minutes == 15
        assert settings.anomaly_threshold_percent == 10.0

    def test_custom_database_url(self, monkeypatch):
        monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
        settings = Settings()
        assert settings.database_url == "sqlite+aiosqlite:///./test.db"

    def test_custom_log_level(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "DEBUG")
        settings = Settings()
        assert settings.log_level == "DEBUG"


class TestPriceRecord:
    def test_price_record_instantiation(self):
        record = PriceRecord(
            source="yfinance",
            product_type="xau_usd",
            buy_price=2650.0,
            sell_price=2651.0,
            price_usd=2650.5,
            price_vnd=None,
            currency="USD",
            timestamp=datetime.now(timezone.utc),
            validation_status="valid",
        )
        assert record.source == "yfinance"
        assert record.product_type == "xau_usd"
        assert record.buy_price == 2650.0
        assert record.sell_price == 2651.0
        assert record.price_usd == 2650.5
        assert record.price_vnd is None
        assert record.currency == "USD"
        assert record.validation_status == "valid"

    def test_price_record_nullable_fields(self):
        record = PriceRecord(
            source="sjc",
            product_type="sjc_bar",
            buy_price=None,
            sell_price=None,
            price_usd=None,
            price_vnd=195000000.0,
            currency="VND",
            validation_status="missing",
        )
        assert record.buy_price is None
        assert record.sell_price is None
        assert record.price_usd is None
        assert record.price_vnd == 195000000.0
        assert record.validation_status == "missing"


class TestDataQualityAlert:
    def test_alert_instantiation(self):
        alert = DataQualityAlert(
            check_type="freshness",
            severity="warning",
            source="yfinance",
            message="No data received in 30 minutes",
        )
        assert alert.check_type == "freshness"
        assert alert.severity == "warning"
        assert alert.source == "yfinance"
        assert alert.message == "No data received in 30 minutes"

    def test_alert_severity_variants(self):
        critical = DataQualityAlert(
            check_type="anomaly",
            severity="critical",
            source="sjc",
            message="Price jumped 25% in 5 minutes",
        )
        assert critical.severity == "critical"


class TestDatabase:
    @pytest.mark.asyncio
    async def test_async_session_factory(self):
        async with async_session() as session:
            assert session is not None

    @pytest.mark.asyncio
    async def test_tables_created_on_init(self):
        await init_db()
        async with async_session() as session:
            result = await session.execute(
                __import__("sqlalchemy").text(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            )
            tables = [row[0] for row in result.fetchall()]
            assert "price_history" in tables
            assert "data_quality_alerts" in tables
