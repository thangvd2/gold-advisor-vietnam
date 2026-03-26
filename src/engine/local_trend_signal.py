from src.engine.types import SignalFactor


def compute_local_trend_signal(local_data: dict, weight: float = 0.1) -> SignalFactor:
    trend_7d = local_data.get("trend_7d")
    trend_30d = local_data.get("trend_30d")
    data_points = local_data.get("data_points", 0)

    if trend_7d is None or data_points < 5:
        return SignalFactor(
            name="local_trend", direction=0.0, weight=weight, confidence=0.0
        )

    if trend_7d < -1.0:
        direction = 0.5
    elif trend_7d < 0.0:
        direction = 0.2
    elif trend_7d <= 0.5:
        direction = 0.0
    elif trend_7d <= 1.0:
        direction = -0.2
    else:
        direction = -0.5

    base_confidence = min(0.8, abs(trend_7d) * 0.5 + 0.3)
    confidence = base_confidence

    if trend_30d is not None:
        trends_agree = (trend_7d < 0 and trend_30d < 0) or (
            trend_7d > 0 and trend_30d > 0
        )
        if trends_agree:
            confidence = min(0.8, confidence * 1.2)
        else:
            confidence *= 0.6

    return SignalFactor(
        name="local_trend", direction=direction, weight=weight, confidence=confidence
    )
