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
    mode_prefix = _mode_prefix(signal.mode)

    if mode_prefix:
        return f"{mode_prefix} {body}"
    return body


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


def _mode_prefix(mode: SignalMode) -> str:
    prefixes = {
        SignalMode.SAVER: "For long-term accumulation:",
        SignalMode.TRADER: "For timing-precision:",
    }
    return prefixes.get(mode, "")
