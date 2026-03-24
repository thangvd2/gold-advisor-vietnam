"""Tests for Vietnamese seasonal demand model (Plan 08-01)."""

import pytest

from src.engine.seasonal import (
    compute_seasonal_modifier,
    compute_seasonal_signal,
    get_month_name,
    get_seasonal_demand_level,
)
from src.engine.types import SignalFactor


class TestGetSeasonalDemandLevel:
    def test_january_is_very_high(self):
        assert get_seasonal_demand_level(1) == "very_high"

    def test_february_is_very_high(self):
        assert get_seasonal_demand_level(2) == "very_high"

    def test_march_is_medium(self):
        assert get_seasonal_demand_level(3) == "medium"

    def test_april_is_medium(self):
        assert get_seasonal_demand_level(4) == "medium"

    def test_may_is_low(self):
        assert get_seasonal_demand_level(5) == "low"

    def test_june_is_low(self):
        assert get_seasonal_demand_level(6) == "low"

    def test_july_is_low(self):
        assert get_seasonal_demand_level(7) == "low"

    def test_august_is_medium(self):
        assert get_seasonal_demand_level(8) == "medium"

    def test_september_is_low(self):
        assert get_seasonal_demand_level(9) == "low"

    def test_october_is_low(self):
        assert get_seasonal_demand_level(10) == "low"

    def test_november_is_high(self):
        assert get_seasonal_demand_level(11) == "high"

    def test_december_is_high(self):
        assert get_seasonal_demand_level(12) == "high"

    def test_invalid_month_zero_raises(self):
        with pytest.raises(ValueError):
            get_seasonal_demand_level(0)

    def test_invalid_month_thirteen_raises(self):
        with pytest.raises(ValueError):
            get_seasonal_demand_level(13)

    def test_invalid_month_negative_raises(self):
        with pytest.raises(ValueError):
            get_seasonal_demand_level(-1)

    def test_all_months_return_valid_levels(self):
        for month in range(1, 13):
            level = get_seasonal_demand_level(month)
            assert level in ("low", "medium", "high", "very_high")


class TestComputeSeasonalModifier:
    def test_very_high_demand_reduces_confidence(self):
        modifier = compute_seasonal_modifier(1)  # January = very_high
        assert modifier == 0.7

    def test_high_demand_moderate_reduction(self):
        modifier = compute_seasonal_modifier(11)  # November = high
        assert modifier == 0.85

    def test_medium_demand_no_change(self):
        modifier = compute_seasonal_modifier(3)  # March = medium
        assert modifier == 1.0

    def test_low_demand_no_change(self):
        modifier = compute_seasonal_modifier(5)  # May = low
        assert modifier == 1.0

    def test_modifier_range(self):
        for month in range(1, 13):
            modifier = compute_seasonal_modifier(month)
            assert 0.7 <= modifier <= 1.0

    def test_february_very_high(self):
        assert compute_seasonal_modifier(2) == 0.7

    def test_august_medium(self):
        assert compute_seasonal_modifier(8) == 1.0

    def test_december_high(self):
        assert compute_seasonal_modifier(12) == 0.85


class TestComputeSeasonalSignal:
    def test_returns_signal_factor(self):
        signal = compute_seasonal_signal(1)
        assert isinstance(signal, SignalFactor)

    def test_name_is_seasonal(self):
        signal = compute_seasonal_signal(1)
        assert signal.name == "seasonal"

    def test_direction_is_zero(self):
        signal = compute_seasonal_signal(1)
        assert signal.direction == 0.0

    def test_weight_is_zero(self):
        signal = compute_seasonal_signal(1)
        assert signal.weight == 0.0

    def test_confidence_stores_modifier(self):
        signal = compute_seasonal_signal(1)  # January = very_high
        assert signal.confidence == 0.7

    def test_low_demand_modifier(self):
        signal = compute_seasonal_signal(5)  # May = low
        assert signal.confidence == 1.0

    def test_custom_weight_preserved(self):
        signal = compute_seasonal_signal(1, weight=0.05)
        assert signal.weight == 0.05

    def test_no_directional_influence_high_demand(self):
        signal = compute_seasonal_signal(2)  # Tet
        assert signal.direction == 0.0  # Never drives buy/sell


class TestGetMonthName:
    def test_january(self):
        assert get_month_name(1) == "January"

    def test_december(self):
        assert get_month_name(12) == "December"

    def test_invalid_month_raises(self):
        with pytest.raises(ValueError):
            get_month_name(0)
