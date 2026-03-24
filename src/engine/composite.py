from datetime import datetime

from src.engine.types import Signal, SignalFactor, Recommendation, SignalMode

THRESHOLDS = {
    SignalMode.SAVER: (0.05, -0.05),
    SignalMode.TRADER: (0.25, -0.25),
}


def compute_composite_signal(
    factors: list[SignalFactor],
    mode: SignalMode = SignalMode.SAVER,
) -> Signal:
    if not factors:
        return Signal(
            recommendation=Recommendation.HOLD,
            confidence=0,
            factors=[],
            mode=mode,
            timestamp=datetime.now(),
        )

    raw_score = sum(f.direction * f.weight for f in factors)

    buy_threshold, sell_threshold = THRESHOLDS.get(mode, (0.15, -0.15))

    if raw_score > buy_threshold:
        recommendation = Recommendation.BUY
    elif raw_score < sell_threshold:
        recommendation = Recommendation.SELL
    else:
        recommendation = Recommendation.HOLD

    total_weight = sum(f.weight for f in factors)
    confidence = int(sum(f.confidence * f.weight for f in factors) / total_weight * 100)

    return Signal(
        recommendation=recommendation,
        confidence=confidence,
        factors=factors,
        reasoning="",
        mode=mode,
        timestamp=datetime.now(),
    )
