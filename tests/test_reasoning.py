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


# ── Multi-factor analysis (analysis_context) ──────────────────────────────────


class TestAnalysisContext:
    def test_fx_section_with_upward_trend(self):
        """FX data with upward trend appears in reasoning."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": {
                "current_rate": 25450.0,
                "ma_7d": 25200.0,
                "ma_30d": 25000.0,
                "trend": "up",
                "change_pct": 1.0,
            },
            "gold_data": None,
            "dealer_spreads": None,
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "USD/VND" in result
        assert "25,450" in result
        assert "weakening" in result.lower()

    def test_fx_section_with_downward_trend(self):
        """FX data with downward trend shows VND strengthening."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": {
                "current_rate": 25450.0,
                "ma_7d": 25800.0,
                "ma_30d": 26000.0,
                "trend": "down",
                "change_pct": -1.4,
            },
            "gold_data": None,
            "dealer_spreads": None,
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "strengthening" in result.lower()

    def test_gold_section_with_upward_trend(self):
        """Gold data with upward trend shows XAU/USD price and direction."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": None,
            "gold_data": {
                "current_price": 3012.50,
                "ma_7d": 2950.0,
                "ma_30d": 2900.0,
                "trend": "up",
                "momentum": 2.3,
            },
            "dealer_spreads": None,
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "XAU/USD" in result
        assert "3,012" in result
        assert "up" in result.lower()

    def test_spread_section_with_tight_spread(self):
        """Dealer spreads under 0.5% shows favorable trading."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": None,
            "gold_data": None,
            "dealer_spreads": [0.35, 0.4, 0.42],
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "Dealer spread" in result
        assert "Tight" in result

    def test_spread_section_with_wide_spread(self):
        """Dealer spreads over 2% shows unfavorable trading."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.HOLD, gap_pct=4.0)
        analysis_context = {
            "fx_data": None,
            "gold_data": None,
            "dealer_spreads": [2.5, 3.1, 2.8],
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "Dealer spread" in result
        assert "Wide" in result or "high" in result.lower()

    def test_all_contexts_combined(self):
        """All analysis_context fields populated → all sections appear."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": {
                "current_rate": 25450.0,
                "ma_7d": 25200.0,
                "ma_30d": 25000.0,
                "trend": "up",
                "change_pct": 1.0,
            },
            "gold_data": {
                "current_price": 3012.50,
                "ma_7d": 2950.0,
                "ma_30d": 2900.0,
                "trend": "up",
                "momentum": 2.3,
            },
            "dealer_spreads": [0.35, 0.4],
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "USD/VND" in result
        assert "XAU/USD" in result
        assert "Dealer spread" in result
        assert "Gap:" in result

    def test_none_context_graceful(self):
        """analysis_context=None → reasoning still works with gap-only data."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        result = generate_reasoning(signal, analysis_context=None)

        assert "Gap:" in result
        assert "2.8%" in result

    def test_empty_context_dict_graceful(self):
        """Empty analysis_context dict → reasoning still works."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        result = generate_reasoning(signal, analysis_context={})

        assert "Gap:" in result

    def test_fx_neutral_still_shows_rate(self):
        """FX neutral trend still shows the current rate value."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": {
                "current_rate": 25500.0,
                "ma_7d": 25480.0,
                "ma_30d": 25450.0,
                "trend": "neutral",
                "change_pct": 0.2,
            },
            "gold_data": None,
            "dealer_spreads": None,
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "USD/VND" in result
        assert "25,500" in result
        assert "Stable" in result or "stable" in result

    def test_gold_neutral_still_shows_price(self):
        """Gold neutral trend still shows the current price value."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.HOLD, gap_pct=4.0)
        analysis_context = {
            "fx_data": None,
            "gold_data": {
                "current_price": 2950.0,
                "ma_7d": 2948.0,
                "ma_30d": 2945.0,
                "trend": "neutral",
                "momentum": 0.2,
            },
            "dealer_spreads": None,
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "XAU/USD" in result
        assert "2,950" in result

    def test_no_fx_or_gold_data_no_crash(self):
        """Missing fx_data and gold_data does not crash."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8)
        analysis_context = {
            "fx_data": None,
            "gold_data": None,
            "dealer_spreads": None,
        }

        result = generate_reasoning(signal, analysis_context=analysis_context)

        assert "Gap:" in result
        assert "USD/VND" not in result
        assert "XAU/USD" not in result
        assert "Dealer spread" not in result


# ── Conclusion line ──────────────────────────────────────────────────────────


class TestConclusionLine:
    def test_buy_conclusion_lists_supporting_factors(self):
        """BUY conclusion lists factors with direction > 0."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(
            Recommendation.BUY,
            gap_pct=2.8,
        )

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=[{"ma_30d": 4.5}]
        )

        assert "=> BUY" in result

    def test_sell_conclusion_lists_supporting_factors(self):
        """SELL conclusion lists factors with direction < 0."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(
            Recommendation.SELL,
            gap_pct=6.2,
        )

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=[{"ma_30d": 4.5}]
        )

        assert "=> SELL" in result

    def test_hold_conclusion_shows_mixed(self):
        """HOLD conclusion mentions mixed signals."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(
            Recommendation.HOLD,
            gap_pct=4.5,
        )

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=[{"ma_30d": 4.5}]
        )

        assert "=> HOLD" in result

    def test_conclusion_includes_confidence(self):
        """Conclusion always includes confidence percentage."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8, gap_vnd=5_000_000)

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=[{"ma_30d": 4.5}]
        )

        assert "72%" in result

    def test_gap_vnd_displayed(self):
        """Gap VND amount appears in reasoning when available."""
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal(Recommendation.BUY, gap_pct=2.8, gap_vnd=5_000_000)

        result = generate_reasoning(
            signal, current_gap=None, historical_gaps=[{"ma_30d": 4.5}]
        )

        assert "5,000,000" in result
