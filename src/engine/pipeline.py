from datetime import datetime, timezone

from src.analysis.gap import calculate_current_gap, calculate_historical_gaps
from src.engine.composite import compute_composite_signal
from src.engine.gap_signal import compute_gap_signal
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

    gap_factor = compute_gap_signal(current_gap, historical_gaps)
    spread_factor = compute_spread_signal([])
    trend_factor = compute_trend_signal(current_gap, historical_gaps)

    factors = [gap_factor, spread_factor, trend_factor]

    signal = compute_composite_signal(factors, mode)

    signal.gap_vnd = current_gap.get("gap_vnd")
    signal.gap_pct = current_gap.get("gap_pct")

    signal.reasoning = generate_reasoning(signal, current_gap, historical_gaps)

    return signal
