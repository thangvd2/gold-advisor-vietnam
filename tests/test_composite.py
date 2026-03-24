import pytest

from src.engine.types import SignalFactor, Signal, Recommendation, SignalMode
from src.engine.composite import compute_composite_signal


class TestCompositeAllPositive:
    def test_all_positive_factors_gives_buy(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.8),
            SignalFactor(name="spread", direction=0.5, weight=0.2, confidence=0.6),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.7),
        ]

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.recommendation == Recommendation.BUY
        assert 0 < signal.confidence <= 100
        assert len(signal.factors) == 3
        assert signal.mode == SignalMode.SAVER
        assert signal.reasoning == ""


class TestCompositeAllNegative:
    def test_all_negative_factors_gives_sell(self):
        factors = [
            SignalFactor(name="gap", direction=-0.8, weight=0.5, confidence=0.8),
            SignalFactor(name="spread", direction=-0.5, weight=0.2, confidence=0.6),
            SignalFactor(name="trend", direction=-0.6, weight=0.3, confidence=0.7),
        ]

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.recommendation == Recommendation.SELL


class TestCompositeMixedNeutral:
    def test_mixed_near_zero_gives_hold(self):
        factors = [
            SignalFactor(name="gap", direction=0.05, weight=0.5, confidence=0.3),
            SignalFactor(name="spread", direction=0.0, weight=0.2, confidence=0.2),
            SignalFactor(name="trend", direction=-0.05, weight=0.3, confidence=0.3),
        ]

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.recommendation == Recommendation.HOLD


class TestCompositeExactScore:
    def test_weighted_sum_produces_correct_recommendation(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.8),
            SignalFactor(name="spread", direction=-0.3, weight=0.2, confidence=0.5),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.7),
        ]
        expected_raw = 0.8 * 0.5 + (-0.3) * 0.2 + 0.6 * 0.3
        assert expected_raw == pytest.approx(0.52, abs=0.01)

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.recommendation == Recommendation.BUY


class TestCompositeSaverMode:
    def test_saver_lower_threshold_triggers_buy(self):
        factors = [
            SignalFactor(name="gap", direction=0.1, weight=0.5, confidence=0.4),
            SignalFactor(name="spread", direction=0.0, weight=0.2, confidence=0.3),
            SignalFactor(name="trend", direction=0.05, weight=0.3, confidence=0.3),
        ]
        raw = 0.1 * 0.5 + 0.0 * 0.2 + 0.05 * 0.3
        assert 0.05 < raw < 0.15

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.recommendation == Recommendation.BUY


class TestCompositeTraderMode:
    def test_trader_stricter_threshold_requires_stronger_signal(self):
        factors = [
            SignalFactor(name="gap", direction=0.3, weight=0.5, confidence=0.7),
            SignalFactor(name="spread", direction=0.1, weight=0.2, confidence=0.5),
            SignalFactor(name="trend", direction=0.2, weight=0.3, confidence=0.6),
        ]
        raw = 0.3 * 0.5 + 0.1 * 0.2 + 0.2 * 0.3
        assert 0.15 < raw < 0.25

        saver_signal = compute_composite_signal(factors, SignalMode.SAVER)
        trader_signal = compute_composite_signal(factors, SignalMode.TRADER)

        assert saver_signal.recommendation == Recommendation.BUY
        assert trader_signal.recommendation == Recommendation.HOLD


class TestCompositeConfidence:
    def test_confidence_is_weighted_average_scaled_to_100(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.8),
            SignalFactor(name="spread", direction=0.0, weight=0.2, confidence=0.4),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.6),
        ]
        expected_confidence = (
            (0.8 * 0.5 + 0.4 * 0.2 + 0.6 * 0.3) / (0.5 + 0.2 + 0.3) * 100
        )
        assert expected_confidence == pytest.approx(66.0)

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.confidence == int(expected_confidence)


class TestCompositeEmptyFactors:
    def test_empty_factors_returns_hold_with_zero_confidence(self):
        signal = compute_composite_signal([], SignalMode.SAVER)

        assert signal.recommendation == Recommendation.HOLD
        assert signal.confidence == 0
        assert signal.factors == []


class TestCompositeImportsModeThresholds:
    def test_composite_uses_mode_thresholds_not_local_dict(self):
        import src.engine.composite as composite_module

        assert not hasattr(composite_module, "THRESHOLDS")

    def test_get_mode_thresholds_produces_correct_behavior(self):
        from src.engine.modes import get_mode_thresholds

        assert get_mode_thresholds(SignalMode.SAVER) == (0.05, -0.05)
        assert get_mode_thresholds(SignalMode.TRADER) == (0.25, -0.25)
