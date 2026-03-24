import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from src.engine.fx_signal import compute_fx_signal
from src.engine.types import SignalFactor
from src.storage.models import Base, PriceRecord


@pytest.fixture
def db_with_rising_fx():
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
        session.commit()
    yield path
    os.unlink(path)


@pytest.fixture
def db_with_falling_fx():
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
    yield path
    os.unlink(path)


@pytest.fixture
def db_with_no_fx():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    yield path
    os.unlink(path)


class TestFxSignalRising:
    def test_rising_fx_gives_positive_direction(self, db_with_rising_fx):
        factor = compute_fx_signal(db_with_rising_fx)
        assert isinstance(factor, SignalFactor)
        assert factor.name == "fx_trend"
        assert factor.direction > 0

    def test_rising_fx_has_positive_confidence(self, db_with_rising_fx):
        factor = compute_fx_signal(db_with_rising_fx)
        assert factor.confidence > 0


class TestFxSignalFalling:
    def test_falling_fx_gives_negative_direction(self, db_with_falling_fx):
        factor = compute_fx_signal(db_with_falling_fx)
        assert factor.direction < 0


class TestFxSignalNoData:
    def test_no_fx_data_returns_zero(self, db_with_no_fx):
        factor = compute_fx_signal(db_with_no_fx)
        assert factor.direction == 0.0
        assert factor.confidence == 0.0
        assert factor.weight == 0.1

    def test_custom_weight_preserved(self, db_with_no_fx):
        factor = compute_fx_signal(db_with_no_fx, weight=0.2)
        assert factor.weight == 0.2
