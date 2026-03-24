import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.analysis.macro import calculate_fx_trend, calculate_gold_trend
from src.storage.models import Base, PriceRecord


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        now = datetime.now(timezone.utc)
        for i in range(40):
            ts = now - timedelta(days=40 - i)
            session.add(
                PriceRecord(
                    source="vietcombank",
                    product_type="usd_vnd",
                    sell_price=24000.0 + i * 100.0,
                    currency="VND",
                    timestamp=ts,
                )
            )
            session.add(
                PriceRecord(
                    source="yfinance",
                    product_type="xau_usd",
                    price_usd=2400.0 + i * 10.0,
                    currency="USD",
                    timestamp=ts,
                )
            )
        session.commit()
    yield path
    os.unlink(path)


class TestFxTrend:
    def test_returns_trend_with_rising_fx(self, db_path):
        result = calculate_fx_trend(db_path)
        assert result is not None
        assert "current_rate" in result
        assert "ma_7d" in result
        assert "trend" in result
        assert result["trend"] == "up"

    def test_returns_none_on_empty_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        try:
            result = calculate_fx_trend(path)
            assert result is None
        finally:
            os.unlink(path)

    def test_fx_change_pct_positive_for_rising(self, db_path):
        result = calculate_fx_trend(db_path)
        assert result is not None
        assert result["change_pct"] > 0


class TestGoldTrend:
    def test_returns_trend_with_rising_gold(self, db_path):
        result = calculate_gold_trend(db_path)
        assert result is not None
        assert "current_price" in result
        assert "ma_7d" in result
        assert "trend" in result
        assert result["trend"] == "up"

    def test_returns_none_on_empty_db(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        try:
            result = calculate_gold_trend(path)
            assert result is None
        finally:
            os.unlink(path)

    def test_gold_momentum_positive_for_rising(self, db_path):
        result = calculate_gold_trend(db_path)
        assert result is not None
        assert result["momentum"] > 0


class TestFxTrendWithFallingPrices:
    def test_falling_fx_gives_down_trend(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(f"sqlite:///{path}")
        Base.metadata.create_all(engine)
        with Session(engine) as session:
            now = datetime.now(timezone.utc)
            for i in range(40):
                ts = now - timedelta(days=40 - i)
                session.add(
                    PriceRecord(
                        source="vietcombank",
                        product_type="usd_vnd",
                        sell_price=28000.0 - i * 100.0,
                        currency="VND",
                        timestamp=ts,
                    )
                )
            session.commit()
        try:
            result = calculate_fx_trend(path)
            assert result is not None
            assert result["trend"] == "down"
            assert result["change_pct"] < 0
        finally:
            os.unlink(path)
