import pytest

from src.engine.types import SignalFactor
from src.engine.spread_signal import compute_spread_signal


class TestSpreadSignalTight:
    def test_tight_spread_0_5_gives_positive_direction(self):
        dealer_spreads = [0.4, 0.5, 0.6]

        factor = compute_spread_signal(dealer_spreads)

        assert isinstance(factor, SignalFactor)
        assert factor.name == "spread"
        assert factor.direction > 0
        assert factor.weight == 0.2
        assert factor.confidence > 0


class TestSpreadSignalWide:
    def test_wide_spread_2_gives_negative_direction(self):
        dealer_spreads = [1.8, 2.0, 2.2]

        factor = compute_spread_signal(dealer_spreads)

        assert factor.direction < 0
        assert factor.weight == 0.2


class TestSpreadSignalModerate:
    def test_moderate_spread_1_2_gives_near_zero(self):
        dealer_spreads = [1.1, 1.2, 1.3]

        factor = compute_spread_signal(dealer_spreads)

        assert abs(factor.direction) < 0.2


class TestSpreadSignalNoData:
    def test_no_spread_data_returns_zero(self):
        factor = compute_spread_signal([])

        assert factor.direction == 0.0
        assert factor.confidence == 0.0
        assert factor.weight == 0.2


class TestSpreadSignalClamping:
    def test_very_tight_spread_clamped_to_0_5(self):
        dealer_spreads = [0.01, 0.02, 0.01]

        factor = compute_spread_signal(dealer_spreads)

        assert -0.5 <= factor.direction <= 0.5
        assert factor.direction > 0.3

    def test_very_wide_spread_clamped_to_neg0_5(self):
        dealer_spreads = [5.0, 6.0, 7.0]

        factor = compute_spread_signal(dealer_spreads)

        assert -0.5 <= factor.direction <= 0.5
        assert factor.direction < -0.3
