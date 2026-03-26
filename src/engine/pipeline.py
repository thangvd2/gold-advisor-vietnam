from datetime import datetime, timezone

from src.analysis.gap import (
    calculate_current_gap,
    calculate_dealer_spreads,
    calculate_historical_gaps,
    get_local_ring_gold_data,
)
from src.analysis.macro import calculate_fx_trend, calculate_gold_trend
from src.engine.composite import compute_composite_signal
from src.engine.fx_signal import compute_fx_signal
from src.engine.gap_signal import compute_gap_signal
from src.engine.gold_trend_signal import compute_gold_trend_signal
from src.engine.local_spread_signal import compute_local_spread_signal
from src.engine.local_trend_signal import compute_local_trend_signal
from src.engine.modes import get_mode_weights
from src.engine.policy import compute_policy_signal
from src.engine.reasoning import generate_reasoning
from src.engine.seasonal import (
    compute_seasonal_signal,
    get_seasonal_demand_level,
    get_month_name,
)
from src.engine.spread_signal import compute_spread_signal
from src.engine.trend_signal import compute_trend_signal
from src.engine.types import Recommendation, Signal, SignalMode


def _current_month() -> int:
    return datetime.now(timezone.utc).month


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
    local_data = get_local_ring_gold_data(db_path)
    fx_data = calculate_fx_trend(db_path)
    gold_data = calculate_gold_trend(db_path)
    mode_weights = get_mode_weights(mode)

    gap_factor = compute_gap_signal(
        current_gap, historical_gaps, weight=mode_weights["gap"]
    )
    spread_factor = compute_spread_signal(dealer_spreads, weight=mode_weights["spread"])
    trend_factor = compute_trend_signal(
        current_gap, historical_gaps, weight=mode_weights["trend"]
    )
    fx_factor = compute_fx_signal(db_path, weight=mode_weights["fx_trend"])
    gold_trend_factor = compute_gold_trend_signal(
        db_path, weight=mode_weights["gold_trend"]
    )
    local_spread_factor = compute_local_spread_signal(
        local_data, dealer_spreads, weight=mode_weights["local_spread"]
    )
    local_trend_factor = compute_local_trend_signal(
        local_data, weight=mode_weights["local_trend"]
    )

    factors = [
        gap_factor,
        spread_factor,
        trend_factor,
        fx_factor,
        gold_trend_factor,
        local_spread_factor,
        local_trend_factor,
    ]

    month = _current_month()
    seasonal_factor = compute_seasonal_signal(month)
    factors.append(seasonal_factor)

    policy_override = compute_policy_signal(db_path)

    seasonal_demand_level = get_seasonal_demand_level(month)
    seasonal_info = {
        "month": month,
        "demand_level": seasonal_demand_level,
        "modifier": seasonal_factor.confidence,
    }

    analysis_context = {
        "fx_data": fx_data,
        "gold_data": gold_data,
        "dealer_spreads": dealer_spreads,
        "local_data": local_data,
    }

    signal = compute_composite_signal(
        factors,
        mode,
        policy_override=policy_override,
        seasonal_modifier=seasonal_factor.confidence,
    )

    signal.gap_vnd = current_gap.get("gap_vnd")
    signal.gap_pct = current_gap.get("gap_pct")

    signal.reasoning = generate_reasoning(
        signal,
        current_gap,
        historical_gaps,
        seasonal_info=seasonal_info,
        policy_info=policy_override,
        analysis_context=analysis_context,
    )

    return signal
