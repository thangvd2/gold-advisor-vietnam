"""Tests for reasoning generator — deterministic one-line signal explanations."""

from datetime import datetime

import pytest

from src.engine.types import Recommendation, Signal, SignalFactor, SignalMode


# ── Helpers ────────────────────────────────────────────────────────────────────


def _make_signal(
    recommendation: Recommendation = Recommendation.BUY,
    gap_pct: float | None = 2.8,
    gap_vnd: float | None = 5_000_000,
    mode: SignalMode = SignalMode.SAVER,
) -> Signal:
    return Signal(
        recommendation=recommendation,
        confidence=72,
        factors=[
            SignalFactor(name="gap", direction=0.5, weight=0.6, confidence=0.8),
        ],
        mode=mode,
        timestamp=datetime(2026, 3, 24, 12, 0, 0),
        gap_vnd=gap_vnd,
        gap_pct=gap_pct,
    )


# ── BUY reasoning ─────────────────────────────────────────────────────────────


class TestBuyReasoning:
    def test_buy_includes_actual_gap_and_ma_values(self):
        """BUY signal reasoning must contain gap_pct and MA values."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        assert "2.8%" in result
        assert "4.5%" in result

    def test_buy_uses_observational_language(self):
        """BUY reasoning must use observational language, not prediction."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        forbidden = ["will ", "expected", "predict", "forecast", "guarantee"]
        for word in forbidden:
            assert word.lower() not in result.lower(), f"Found forbidden word: {word}"


# ── SELL reasoning ────────────────────────────────────────────────────────────


class TestSellReasoning:
    def test_sell_includes_actual_gap_and_ma_values(self):
        """SELL signal reasoning must contain gap_pct and MA values."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.SELL, gap_pct=6.2)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        assert "6.2%" in result
        assert "4.5%" in result

    def test_sell_no_prediction_language(self):
        """SELL reasoning must not contain prediction words."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.SELL, gap_pct=6.2)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        forbidden = ["will ", "expected", "predict", "forecast", "guarantee"]
        for word in forbidden:
            assert word.lower() not in result.lower(), f"Found forbidden word: {word}"


# ── HOLD reasoning ────────────────────────────────────────────────────────────


class TestHoldReasoning:
    def test_hold_near_avg_language(self):
        """HOLD reasoning when gap near average should mention 'near' or 'close to'."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.HOLD, gap_pct=4.3)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        assert "near" in result.lower() or "close to" in result.lower()
        assert "4.3%" in result
        assert "4.5%" in result


# ── Mode prefixes ─────────────────────────────────────────────────────────────


class TestModePrefix:
    def test_saver_mode_adds_accumulation_prefix(self):
        """Saver mode reasoning starts with accumulation-oriented prefix."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8, mode=SignalMode.SAVER)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        assert result.startswith("For long-term accumulation:")

    def test_trader_mode_adds_timing_prefix(self):
        """Trader mode reasoning starts with timing-precision prefix."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8, mode=SignalMode.TRADER)
        historical_gaps = [{"ma_30d": 4.5}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        assert result.startswith("For timing-precision:")


# ── No gap data ───────────────────────────────────────────────────────────────


class TestNoGapData:
    def test_no_gap_data_returns_insufficient_message(self):
        """When gap_pct is None and no current_gap, return insufficient data message."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.HOLD, gap_pct=None, gap_vnd=None)
        result = generate_reasoning(signal, current_gap=None, historical_gaps=None)

        assert "Insufficient data" in result or "insufficient" in result.lower()

    def test_no_historical_gaps_uses_signal_gap_only(self):
        """No historical_gaps but signal has gap_pct → reasoning still works."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        result = generate_reasoning(signal, current_gap=None, historical_gaps=None)

        assert "2.8%" in result


# ── MA fallback ───────────────────────────────────────────────────────────────


class TestMaFallback:
    def test_falls_back_to_ma_7d_when_no_ma_30d(self):
        """If ma_30d is None but ma_7d exists, use ma_7d."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        historical_gaps = [{"ma_30d": None, "ma_7d": 3.2}]

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=historical_gaps
        )

        assert "3.2%" in result
