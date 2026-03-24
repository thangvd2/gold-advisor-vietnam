from src.analysis.macro import calculate_gold_trend
from src.engine.types import SignalFactor


def compute_gold_trend_signal(db_path: str, weight: float = 0.1) -> SignalFactor:
    gold_data = calculate_gold_trend(db_path)

    if gold_data is None:
        return SignalFactor(
            name="gold_trend", direction=0.0, weight=weight, confidence=0.0
        )

    trend = gold_data["trend"]
    momentum = gold_data["momentum"]

    if trend == "up":
        direction = min(0.5, 0.2 + abs(momentum) / 10.0)
    elif trend == "down":
        direction = max(-0.5, -(0.2 + abs(momentum) / 10.0))
    else:
        direction = 0.0

    confidence = min(0.8, max(0.1, abs(momentum) / 5.0))

    return SignalFactor(
        name="gold_trend", direction=direction, weight=weight, confidence=confidence
    )
