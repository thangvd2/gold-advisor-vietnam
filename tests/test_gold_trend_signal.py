import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.engine.gold_trend_signal import compute_gold_trend_signal
from src.engine.types import SignalFactor
from src.storage.models import Base, PriceRecord


@pytest.fixture
def db_with_rising_gold():
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


@pytest.fixture
def db_with_falling_gold():
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
                    source="yfinance",
                    product_type="xau_usd",
                    price_usd=2800.0 - i * 10.0,
                    currency="USD",
                    timestamp=ts,
                )
            )
        session.commit()
    yield path
    os.unlink(path)


@pytest.fixture
def db_with_no_gold():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    yield path
    os.unlink(path)


class TestGoldTrendSignalRising:
    def test_rising_gold_gives_positive_direction(self, db_with_rising_gold):
        factor = compute_gold_trend_signal(db_with_rising_gold)
        assert isinstance(factor, SignalFactor)
        assert factor.name == "gold_trend"
        assert factor.direction > 0

    def test_rising_gold_has_confidence(self, db_with_rising_gold):
        factor = compute_gold_trend_signal(db_with_rising_gold)
        assert factor.confidence > 0


class TestGoldTrendSignalFalling:
    def test_falling_gold_gives_negative_direction(self, db_with_falling_gold):
        factor = compute_gold_trend_signal(db_with_falling_gold)
        assert factor.direction < 0


class TestGoldTrendSignalNoData:
    def test_no_gold_data_returns_zero(self, db_with_no_gold):
        factor = compute_gold_trend_signal(db_with_no_gold)
        assert factor.direction == 0.0
        assert factor.confidence == 0.0
        assert factor.weight == 0.1

    def test_custom_weight_preserved(self, db_with_no_gold):
        factor = compute_gold_trend_signal(db_with_no_gold, weight=0.2)
        assert factor.weight == 0.2
