from datetime import datetime, timezone

from src.analysis.gap import (
    calculate_current_gap,
    calculate_dealer_spreads,
    calculate_historical_gaps,
)
from src.engine.composite import compute_composite_signal
from src.engine.gap_signal import compute_gap_signal
from src.engine.modes import get_mode_weights
from src.engine.reasoning import generate_reasoning
from src.engine.spread_signal import compute_spread_signal
from src.engine.trend_signal import compute_trend_signal
from src.engine.types import Recommendation, Signal, SignalMode


def compute_signal(db_path: str, mode: SignalMode = SignalMode.SAVER) -> Signal:
    current_gap = calculate_current_gap(db_path)

    if current_gap is None:
        return Signal(
            recommendation=Recommendation.HOLD,
            confidence=0,
            factors=[],
            reasoning="Insufficient data for signal analysis",
            mode=mode,
            timestamp=datetime.now(timezone.utc),
            gap_vnd=None,
            gap_pct=None,
        )

    historical_gaps = calculate_historical_gaps(db_path, range="1M")
    dealer_spreads = calculate_dealer_spreads(db_path)
    mode_weights = get_mode_weights(mode)

    gap_factor = compute_gap_signal(
        current_gap, historical_gaps, weight=mode_weights["gap"]
    )
    spread_factor = compute_spread_signal(dealer_spreads, weight=mode_weights["spread"])
    trend_factor = compute_trend_signal(
        current_gap, historical_gaps, weight=mode_weights["trend"]
    )

    factors = [gap_factor, spread_factor, trend_factor]

    signal = compute_composite_signal(factors, mode)

    signal.gap_vnd = current_gap.get("gap_vnd")
    signal.gap_pct = current_gap.get("gap_pct")

    signal.reasoning = generate_reasoning(signal, current_gap, historical_gaps)

    return signal
