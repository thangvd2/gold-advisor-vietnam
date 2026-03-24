import pytest

from src.engine.types import SignalFactor, Signal, Recommendation, SignalMode
from src.engine.trend_signal import compute_trend_signal
from src.engine.composite import compute_composite_signal


def _make_current(gap_pct=3.0, gap_vnd=2_700_000, **kwargs) -> dict:
    return {
        "gap_vnd": gap_vnd,
        "gap_pct": gap_pct,
        "avg_sjc_sell": kwargs.get("avg_sjc_sell", 95_000_000),
        "intl_price_vnd": kwargs.get("intl_price_vnd", 92_300_000),
        "intl_price_usd": kwargs.get("intl_price_usd", 2950.0),
        "dealer_count": kwargs.get("dealer_count", 4),
        "timestamp": "2026-03-25T00:00:00+00:00",
    }


def _make_historical(
    gap_vnds: list[float], ma_7d: float | None = None, ma_30d: float | None = None
) -> list[dict]:
    entries = []
    base_date = 24 - len(gap_vnds)
    for i, gv in enumerate(gap_vnds):
        entry = {
            "timestamp": f"2026-03-{base_date + i + 1:02d}T00:00:00+00:00",
            "gap_vnd": gv,
            "gap_pct": gv / 900_000,
            "ma_7d": ma_7d,
            "ma_30d": ma_30d,
        }
        entries.append(entry)
    return entries


class TestTrendNarrowing:
    def test_narrowing_gap_gives_positive_direction(self):
        current = _make_current(gap_vnd=2_000_000)
        historical = _make_historical(
            [
                3_500_000,
                3_300_000,
                3_100_000,
                2_900_000,
                2_700_000,
                2_500_000,
                2_300_000,
            ]
        )

        factor = compute_trend_signal(current, historical)

        assert factor.direction > 0
        assert factor.weight == 0.3
        assert factor.confidence > 0


class TestTrendWidening:
    def test_widening_gap_gives_negative_direction(self):
        current = _make_current(gap_vnd=3_500_000)
        historical = _make_historical(
            [
                2_000_000,
                2_200_000,
                2_400_000,
                2_600_000,
                2_800_000,
                3_000_000,
                3_200_000,
            ]
        )

        factor = compute_trend_signal(current, historical)

        assert factor.direction < 0
        assert factor.weight == 0.3


class TestTrendMACrossover:
    def test_7d_crosses_below_30d_bullish(self):
        current = _make_current()
        historical = _make_historical(
            [3_000_000] * 10, ma_7d=2_800_000, ma_30d=3_200_000
        )

        factor = compute_trend_signal(current, historical)

        assert factor.direction > 0

    def test_7d_crosses_above_30d_bearish(self):
        current = _make_current()
        historical = _make_historical(
            [3_000_000] * 10, ma_7d=3_400_000, ma_30d=3_000_000
        )

        factor = compute_trend_signal(current, historical)

        assert factor.direction < 0


class TestTrendInsufficientData:
    def test_less_than_7_days_returns_zero(self):
        current = _make_current()
        historical = _make_historical([2_000_000, 2_100_000, 2_200_000])

        factor = compute_trend_signal(current, historical)

        assert factor.direction == 0.0
        assert factor.confidence == 0.0


class TestTrendClamping:
    def test_direction_clamped_to_range(self):
        current = _make_current(gap_vnd=100_000)
        historical = _make_historical(
            [
                9_000_000,
                8_000_000,
                7_000_000,
                6_000_000,
                5_000_000,
                4_000_000,
                3_000_000,
            ]
        )

        factor = compute_trend_signal(current, historical)

        assert -1.0 <= factor.direction <= 1.0


class TestCompositeAllPositive:
    def test_all_positive_factors_gives_buy(self):
        factors = [
            SignalFactor(name="gap", direction=0.8, weight=0.5, confidence=0.8),
            SignalFactor(name="spread", direction=0.5, weight=0.2, confidence=0.6),
            SignalFactor(name="trend", direction=0.6, weight=0.3, confidence=0.7),
        ]

        signal = compute_composite_signal(factors, SignalMode.SAVER)

        assert signal.recommendation == Recommendation.BUY


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
