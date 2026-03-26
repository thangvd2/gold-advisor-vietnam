from statistics import mean

from src.engine.types import SignalFactor


def compute_local_spread_signal(
    local_data: dict,
    dealer_spreads: list[float] | None = None,
    weight: float = 0.1,
) -> SignalFactor:
    spread_pct = local_data.get("spread_pct")
    if spread_pct is None:
        return SignalFactor(
            name="local_spread", direction=0.0, weight=weight, confidence=0.0
        )

    if dealer_spreads:
        avg_dealer_spread = mean(dealer_spreads)
        spread_diff = spread_pct - avg_dealer_spread

        if spread_diff < 0:
            direction = 0.3
        elif spread_diff <= 0.5:
            direction = 0.0
        elif spread_diff <= 1.5:
            direction = -0.2
        else:
            direction = -0.4

        confidence = min(0.7, max(0.3, 0.4 + abs(spread_diff) * 0.2))
    else:
        if spread_pct < 1.5:
            direction = 0.2
        elif spread_pct < 3.0:
            direction = 0.0
        elif spread_pct < 5.0:
            direction = -0.2
        else:
            direction = -0.4

        confidence = 0.3

    return SignalFactor(
        name="local_spread", direction=direction, weight=weight, confidence=confidence
    )
