"""Tests for mode-specific signal interpretation — weights and thresholds."""

import pytest

from src.engine.types import SignalMode


# ── get_mode_weights ──────────────────────────────────────────────────────────


class TestGetModeWeights:
    def test_saver_weights(self):
        """Saver mode: trend-heavy weights (trend=0.5, gap=0.4, spread=0.1)."""
        from src.engine.modes import get_mode_weights

        weights = get_mode_weights(SignalMode.SAVER)

        assert weights["gap"] == 0.4
        assert weights["spread"] == 0.1
        assert weights["trend"] == 0.5

    def test_trader_weights(self):
        """Trader mode: gap-heavy weights (gap=0.6, spread=0.3, trend=0.1)."""
        from src.engine.modes import get_mode_weights

        weights = get_mode_weights(SignalMode.TRADER)

        assert weights["gap"] == 0.6
        assert weights["spread"] == 0.3
        assert weights["trend"] == 0.1

    def test_saver_weights_sum_to_one(self):
        """Saver mode weights must sum to 1.0."""
        from src.engine.modes import get_mode_weights

        weights = get_mode_weights(SignalMode.SAVER)
        total = sum(weights.values())

        assert total == pytest.approx(1.0)

    def test_trader_weights_sum_to_one(self):
        """Trader mode weights must sum to 1.0."""
        from src.engine.modes import get_mode_weights

        weights = get_mode_weights(SignalMode.TRADER)
        total = sum(weights.values())

        assert total == pytest.approx(1.0)


# ── get_mode_thresholds ───────────────────────────────────────────────────────


class TestGetModeThresholds:
    def test_saver_thresholds(self):
        """Saver mode: relaxed thresholds (0.05, -0.05)."""
        from src.engine.modes import get_mode_thresholds

        buy_th, sell_th = get_mode_thresholds(SignalMode.SAVER)

        assert buy_th == 0.05
        assert sell_th == -0.05

    def test_trader_thresholds(self):
        """Trader mode: strict thresholds (0.25, -0.25)."""
        from src.engine.modes import get_mode_thresholds

        buy_th, sell_th = get_mode_thresholds(SignalMode.TRADER)

        assert buy_th == 0.25
        assert sell_th == -0.25
