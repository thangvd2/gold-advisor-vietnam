from statistics import mean, stdev

from src.engine.types import SignalFactor

MIN_DATA_POINTS = 7


def compute_trend_signal(
    current_gap: dict, historical_gaps: list[dict]
) -> SignalFactor:
    valid_gaps = [
        entry["gap_vnd"]
        for entry in historical_gaps
        if entry.get("gap_vnd") is not None
    ]

    if len(valid_gaps) < MIN_DATA_POINTS:
        return SignalFactor(name="trend", direction=0.0, weight=0.3, confidence=0.0)

    mid = len(valid_gaps) // 2
    first_half_avg = mean(valid_gaps[:mid])
    second_half_avg = mean(valid_gaps[mid:])

    if first_half_avg == 0:
        trend_direction = 0.0
    else:
        trend_change = (second_half_avg - first_half_avg) / first_half_avg
        trend_direction = max(-1.0, min(1.0, -trend_change * 3.0))

    last_entry = historical_gaps[-1]
    ma_7d = last_entry.get("ma_7d")
    ma_30d = last_entry.get("ma_30d")

    crossover_signal = 0.0
    if ma_7d is not None and ma_30d is not None and ma_30d > 0:
        ma_diff = (ma_7d - ma_30d) / ma_30d
        crossover_signal = max(-0.5, min(0.5, -ma_diff * 3.0))

    combined = trend_direction * 0.7 + crossover_signal * 0.3
    direction = max(-1.0, min(1.0, combined))

    if len(valid_gaps) >= 2:
        gap_stdev = stdev(valid_gaps)
        avg_gap = mean(valid_gaps)
        variability = gap_stdev / avg_gap if avg_gap > 0 else 1.0
        confidence = max(0.1, min(0.9, 1.0 - variability * 2.0))
    else:
        confidence = 0.1

    return SignalFactor(
        name="trend", direction=direction, weight=0.3, confidence=confidence
    )
