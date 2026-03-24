import pytest

from src.engine.types import SignalFactor, Signal, Recommendation, SignalMode
from src.engine.composite import compute_composite_signal


class TestCompositePolicyOverride:
    def test_high_severity_policy_caps_confidence_at_30(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.9),
            SignalFactor(name="spread", direction=0.5, weight=0.2, confidence=0.8),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.85),
        ]
        policy_override = {
            "has_override": True,
            "confidence_cap": 0.3,
            "override_type": "bearish",
            "summary": "SBV auction announced",
        }

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            policy_override=policy_override,
        )

        assert signal.confidence <= 30

    def test_medium_severity_policy_caps_confidence_at_60(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.9),
            SignalFactor(name="spread", direction=0.5, weight=0.2, confidence=0.8),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.85),
        ]
        policy_override = {
            "has_override": True,
            "confidence_cap": 0.6,
            "override_type": "bullish",
            "summary": "Import licenses approved",
        }

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            policy_override=policy_override,
        )

        assert signal.confidence <= 60

    def test_no_override_preserves_normal_confidence(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.9),
            SignalFactor(name="spread", direction=0.5, weight=0.2, confidence=0.8),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.85),
        ]
        policy_override = {
            "has_override": False,
            "confidence_cap": 1.0,
            "override_type": None,
            "summary": "No active events",
        }

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            policy_override=policy_override,
        )

        expected = int((0.9 * 0.5 + 0.8 * 0.2 + 0.85 * 0.3) / (0.5 + 0.2 + 0.3) * 100)
        assert signal.confidence == expected

    def test_policy_takes_priority_over_seasonal(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.9),
        ]
        policy_override = {
            "has_override": True,
            "confidence_cap": 0.3,
            "override_type": "bearish",
            "summary": "SBV intervention",
        }

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            policy_override=policy_override,
            seasonal_modifier=1.0,
        )

        assert signal.confidence <= 30


class TestCompositeSeasonalModifier:
    def test_seasonal_modifier_reduces_confidence(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.8),
            SignalFactor(name="spread", direction=0.5, weight=0.2, confidence=0.6),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.7),
        ]

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            seasonal_modifier=0.7,
        )

        base_confidence = int(
            (0.8 * 0.5 + 0.6 * 0.2 + 0.7 * 0.3) / (0.5 + 0.2 + 0.3) * 100
        )
        expected = int(base_confidence * 0.7)
        assert signal.confidence == expected

    def test_seasonal_modifier_1_0_no_change(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.8),
        ]

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            seasonal_modifier=1.0,
        )

        assert signal.confidence == 80

    def test_both_policy_and_seasonal_applied(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.9),
        ]
        policy_override = {
            "has_override": True,
            "confidence_cap": 0.6,
            "override_type": "bullish",
            "summary": "Import approved",
        }

        signal = compute_composite_signal(
            factors,
            SignalMode.SAVER,
            policy_override=policy_override,
            seasonal_modifier=0.85,
        )

        seasonal_conf = int(90 * 0.85)
        assert signal.confidence == min(seasonal_conf, 60)
