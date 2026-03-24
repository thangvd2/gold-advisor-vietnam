from datetime import datetime

import pytest

from src.engine.types import Recommendation, Signal, SignalFactor, SignalMode


def _make_signal(
    recommendation: Recommendation = Recommendation.BUY,
    gap_pct: float = 2.8,
    mode: SignalMode = SignalMode.SAVER,
) -> Signal:
    return Signal(
        recommendation=recommendation,
        confidence=72,
        factors=[SignalFactor(name="gap", direction=0.5, weight=0.6, confidence=0.8)],
        mode=mode,
        timestamp=datetime(2026, 3, 24, 12, 0, 0),
        gap_pct=gap_pct,
    )


class TestSeasonalReasoning:
    def test_high_demand_season_included(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()
        seasonal_info = {"month": 1, "demand_level": "very_high", "modifier": 0.7}

        result = generate_reasoning(
            signal,
            seasonal_info=seasonal_info,
        )

        assert "demand" in result.lower()

    def test_low_demand_season_not_mentioned(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()
        seasonal_info = {"month": 5, "demand_level": "low", "modifier": 1.0}

        result = generate_reasoning(
            signal,
            seasonal_info=seasonal_info,
        )

        assert "high demand" not in result.lower()

    def test_month_name_in_reasoning(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()
        seasonal_info = {"month": 2, "demand_level": "very_high", "modifier": 0.7}

        result = generate_reasoning(
            signal,
            seasonal_info=seasonal_info,
        )

        assert "february" in result.lower() or "tet" in result.lower()

    def test_no_seasonal_info_graceful(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()

        result = generate_reasoning(signal, seasonal_info=None)

        assert result is not None


class TestPolicyReasoning:
    def test_active_policy_alert_included(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()
        policy_info = {
            "has_override": True,
            "summary": "SBV gold auction announced",
        }

        result = generate_reasoning(signal, policy_info=policy_info)

        assert "policy" in result.lower() or "state bank" in result.lower()

    def test_no_policy_info_graceful(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()

        result = generate_reasoning(signal, policy_info=None)

        assert result is not None

    def test_policy_without_override_not_mentioned(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()
        policy_info = {
            "has_override": False,
            "summary": "No active events",
        }

        result = generate_reasoning(signal, policy_info=policy_info)

        assert "policy" not in result.lower() and "state bank" not in result.lower()


class TestCombinedContext:
    def test_both_seasonal_and_policy_in_reasoning(self):
        from src.engine.reasoning import generate_reasoning

        signal = _make_signal()
        seasonal_info = {"month": 1, "demand_level": "very_high", "modifier": 0.7}
        policy_info = {
            "has_override": True,
            "summary": "SBV auction announced",
        }

        result = generate_reasoning(
            signal,
            seasonal_info=seasonal_info,
            policy_info=policy_info,
        )

        assert "policy" in result.lower() or "state bank" in result.lower()
        assert "demand" in result.lower() or "seasonal" in result.lower()
