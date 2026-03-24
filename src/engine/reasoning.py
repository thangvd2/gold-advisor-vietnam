"""Deterministic one-line reasoning generation from signal data.

Uses f-strings with conditional logic — no LLM involvement.
All reasoning is grounded in actual data values.
"""

from __future__ import annotations

from src.engine.types import Signal, SignalMode


def generate_reasoning(
    signal: Signal,
    current_gap: dict | None = None,
    historical_gaps: list[dict] | None = None,
    seasonal_info: dict | None = None,
    policy_info: dict | None = None,
) -> str:
    gap_pct = None
    if current_gap and "gap_pct" in current_gap:
        gap_pct = current_gap["gap_pct"]
    if gap_pct is None:
        gap_pct = signal.gap_pct

    if gap_pct is None:
        mode_prefix = _mode_prefix(signal.mode)
        if mode_prefix:
            return f"{mode_prefix} Insufficient data for signal analysis"
        return "Insufficient data for signal analysis"

    ma_value = _find_ma(historical_gaps)
    ma_label, ma_display = _format_ma(ma_value)

    body = _build_reasoning_body(signal, gap_pct, ma_label, ma_display)
    macro_context = _build_macro_context(signal.factors)
    seasonal_context = _build_seasonal_context(seasonal_info)
    policy_context = _build_policy_context(policy_info)

    parts = [body]
    if macro_context:
        parts.append(macro_context)
    if seasonal_context:
        parts.append(seasonal_context)
    if policy_context:
        parts.append(policy_context)

    combined_body = ". ".join(parts)

    mode_prefix = _mode_prefix(signal.mode)

    if mode_prefix:
        return f"{mode_prefix} {combined_body}"
    return combined_body


def _find_ma(historical_gaps: list[dict] | None) -> float | None:
    if not historical_gaps:
        return None
    for entry in reversed(historical_gaps):
        if entry.get("ma_30d") is not None:
            return entry["ma_30d"]
    for entry in reversed(historical_gaps):
        if entry.get("ma_7d") is not None:
            return entry["ma_7d"]
    return None


def _format_ma(ma_value: float | None) -> tuple[str, str]:
    if ma_value is not None:
        return "30-day avg", f"{ma_value:.1f}%"
    return "", ""


def _build_reasoning_body(
    signal: Signal, gap_pct: float, ma_label: str, ma_display: str
) -> str:
    gap_str = f"{gap_pct:.1f}%"
    rec = signal.recommendation

    if ma_display:
        if rec == "BUY":
            return (
                f"Gap at {gap_str} vs {ma_label} {ma_display} "
                f"— favorable conditions observed for buying"
            )
        elif rec == "SELL":
            return (
                f"Gap at {gap_str} vs {ma_label} {ma_display} "
                f"— conditions less favorable for selling"
            )
        else:
            return (
                f"Gap at {gap_str} near {ma_label} {ma_display} "
                f"— no strong directional signal"
            )
    else:
        if rec == "BUY":
            return f"Gap at {gap_str} — favorable conditions observed for buying"
        elif rec == "SELL":
            return f"Gap at {gap_str} — conditions less favorable for selling"
        else:
            return f"Gap at {gap_str} — no strong directional signal"


def _build_macro_context(factors: list) -> str:
    parts = []
    for f in factors:
        if f.name == "fx_trend" and f.confidence > 0:
            if f.direction > 0:
                parts.append("VND weakening (USD rising)")
            elif f.direction < 0:
                parts.append("VND strengthening (USD falling)")
        elif f.name == "gold_trend" and f.confidence > 0:
            if f.direction > 0:
                parts.append("global gold trending up")
            elif f.direction < 0:
                parts.append("global gold trending down")
    return "; ".join(parts)


def _build_seasonal_context(seasonal_info: dict | None) -> str:
    if not seasonal_info:
        return ""
    demand_level = seasonal_info.get("demand_level", "")
    month = seasonal_info.get("month", 0)
    if demand_level in ("very_high", "high"):
        from src.engine.seasonal import get_month_name

        month_name = get_month_name(month) if month else ""
        if demand_level == "very_high":
            return f"High demand season ({month_name}) — gap widening is expected"
        return f"Elevated demand ({month_name}) — wider gaps are typical"
    return ""


def _build_policy_context(policy_info: dict | None) -> str:
    if not policy_info:
        return ""
    if not policy_info.get("has_override"):
        return ""
    summary = policy_info.get("summary", "State Bank policy event active")
    return f"State Bank policy alert: {summary}"


def _mode_prefix(mode: SignalMode) -> str:
    prefixes = {
        SignalMode.SAVER: "For long-term accumulation:",
        SignalMode.TRADER: "For timing-precision:",
    }
    return prefixes.get(mode, "")
