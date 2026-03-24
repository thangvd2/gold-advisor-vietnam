from src.analysis.macro import calculate_fx_trend
from src.engine.types import SignalFactor


def compute_fx_signal(db_path: str, weight: float = 0.1) -> SignalFactor:
    fx_data = calculate_fx_trend(db_path)

    if fx_data is None:
        return SignalFactor(
            name="fx_trend", direction=0.0, weight=weight, confidence=0.0
        )

    trend = fx_data["trend"]
    change_pct = fx_data["change_pct"]

    if trend == "up":
        direction = min(0.5, 0.2 + abs(change_pct) / 10.0)
    elif trend == "down":
        direction = max(-0.5, -(0.2 + abs(change_pct) / 10.0))
    else:
        direction = 0.0

    confidence = min(0.8, max(0.1, abs(change_pct) / 5.0))

    return SignalFactor(
        name="fx_trend", direction=direction, weight=weight, confidence=confidence
    )
