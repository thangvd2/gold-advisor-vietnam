from statistics import mean, stdev

from src.engine.types import SignalFactor


def compute_spread_signal(
    dealer_spreads: list[float], weight: float = 0.2
) -> SignalFactor:
    if not dealer_spreads:
        return SignalFactor(name="spread", direction=0.0, weight=weight, confidence=0.0)

    avg_spread = mean(dealer_spreads)

    if avg_spread < 0.5:
        direction = 0.5
    elif avg_spread < 1.0:
        direction = 0.25
    elif avg_spread < 2.0:
        direction = 0.0
    elif avg_spread < 3.0:
        direction = -0.25
    else:
        direction = -0.5

    if len(dealer_spreads) >= 2:
        spread_stdev = stdev(dealer_spreads)
        variability = spread_stdev / avg_spread if avg_spread > 0 else 1.0
        confidence = max(0.1, min(0.9, 1.0 - variability))
    else:
        confidence = 0.3

    return SignalFactor(
        name="spread", direction=direction, weight=weight, confidence=confidence
    )
