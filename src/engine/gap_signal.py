from src.engine.types import SignalFactor


def compute_gap_signal(
    current_gap: dict, historical_gaps: list[dict], weight: float = 0.5
) -> SignalFactor:
    gap_pct = current_gap.get("gap_pct")
    if gap_pct is None:
        return SignalFactor(name="gap", direction=0.0, weight=weight, confidence=0.0)

    if not historical_gaps:
        return SignalFactor(name="gap", direction=0.0, weight=weight, confidence=0.0)

    ma_30d = None
    ma_7d = None
    for entry in reversed(historical_gaps):
        if ma_30d is None and entry.get("ma_30d") is not None:
            ma_30d = entry["ma_30d"]
        if ma_7d is None and entry.get("ma_7d") is not None:
            ma_7d = entry["ma_7d"]
        if ma_30d is not None and ma_7d is not None:
            break

    reference_ma = ma_30d if ma_30d is not None else ma_7d
    if reference_ma is None or reference_ma == 0:
        return SignalFactor(name="gap", direction=0.0, weight=weight, confidence=0.0)

    deviation_pp = gap_pct - reference_ma
    direction = max(-1.0, min(1.0, -deviation_pp * 2.0))

    abs_deviation = abs(deviation_pp)
    confidence = min(0.9, max(0.1, abs_deviation * 3.0))
    if ma_30d is None and ma_7d is not None:
        confidence *= 0.7

    return SignalFactor(
        name="gap", direction=direction, weight=weight, confidence=confidence
    )
