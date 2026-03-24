import pytest

from src.engine.types import SignalFactor
from src.engine.gap_signal import compute_gap_signal


def _make_current(gap_pct: float, **kwargs) -> dict:
    return {
        "gap_vnd": kwargs.get("gap_vnd", 2_000_000),
        "gap_pct": gap_pct,
        "avg_sjc_sell": kwargs.get("avg_sjc_sell", 95_000_000),
        "intl_price_vnd": kwargs.get("intl_price_vnd", 93_000_000),
        "intl_price_usd": kwargs.get("intl_price_usd", 2950.0),
        "dealer_count": kwargs.get("dealer_count", 4),
        "timestamp": "2026-03-25T00:00:00+00:00",
    }


def _make_historical(
    gap_pcts: list[float], ma_7d: float | None = None, ma_30d: float | None = None
) -> list[dict]:
    entries = []
    for i, gp in enumerate(gap_pcts):
        entry = {
            "timestamp": f"2026-03-{24 - len(gap_pcts) + i + 1:02d}T00:00:00+00:00",
            "gap_vnd": gp * 900_000,
            "gap_pct": gp,
            "ma_7d": ma_7d,
            "ma_30d": ma_30d,
        }
        entries.append(entry)
    return entries


def _make_historical_with_mas(
    gap_pcts: list[float], ma_7d: float, ma_30d: float
) -> list[dict]:
    entries = _make_historical(gap_pcts)
    for entry in entries:
        entry["ma_7d"] = ma_7d
        entry["ma_30d"] = ma_30d
    return entries


class TestGapSignalNarrowing:
    def test_gap_narrowing_vs_30d_ma_gives_positive_direction(self):
        current = _make_current(gap_pct=2.8)
        historical = _make_historical_with_mas([3.0, 3.5, 4.0], ma_7d=3.5, ma_30d=4.5)

        factor = compute_gap_signal(current, historical)

        assert isinstance(factor, SignalFactor)
        assert factor.name == "gap"
        assert factor.direction > 0
        assert factor.weight == 0.5
        assert factor.confidence > 0.3


class TestGapSignalWidening:
    def test_gap_widening_vs_30d_ma_gives_negative_direction(self):
        current = _make_current(gap_pct=6.0)
        historical = _make_historical_with_mas([4.0, 4.2, 4.5], ma_7d=4.5, ma_30d=4.5)

        factor = compute_gap_signal(current, historical)

        assert factor.direction < 0
        assert factor.weight == 0.5


class TestGapSignalNeutral:
    def test_gap_at_30d_ma_gives_near_zero_direction(self):
        current = _make_current(gap_pct=4.5)
        historical = _make_historical_with_mas([4.5, 4.4, 4.6], ma_7d=4.5, ma_30d=4.5)

        factor = compute_gap_signal(current, historical)

        assert abs(factor.direction) < 0.2


class TestGapSignalNoHistory:
    def test_no_historical_data_returns_zero_signal(self):
        current = _make_current(gap_pct=3.0)

        factor = compute_gap_signal(current, [])

        assert factor.direction == 0.0
        assert factor.confidence == 0.0
        assert factor.weight == 0.5

    def test_no_30d_ma_uses_7d_ma(self):
        current = _make_current(gap_pct=2.8)
        historical = _make_historical([3.0, 3.5, 4.0])
        for entry in historical:
            entry["ma_7d"] = 3.5
            entry["ma_30d"] = None

        factor = compute_gap_signal(current, historical)

        assert factor.direction > 0
        assert factor.confidence > 0


class TestGapSignalClamping:
    def test_extreme_gap_difference_clamped_to_1(self):
        current = _make_current(gap_pct=20.0)
        historical = _make_historical_with_mas([4.0], ma_7d=4.5, ma_30d=4.5)

        factor = compute_gap_signal(current, historical)

        assert -1.0 <= factor.direction <= 1.0

    def test_extreme_narrow_gap_clamped_to_neg1(self):
        current = _make_current(gap_pct=0.1)
        historical = _make_historical_with_mas([4.0], ma_7d=4.5, ma_30d=4.5)

        factor = compute_gap_signal(current, historical)

        assert -1.0 <= factor.direction <= 1.0
        assert factor.direction > 0
