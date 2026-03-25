from __future__ import annotations

from src.engine.types import Signal, SignalMode


def generate_reasoning(
    signal: Signal,
    current_gap: dict | None = None,
    historical_gaps: list[dict] | None = None,
    seasonal_info: dict | None = None,
    policy_info: dict | None = None,
    analysis_context: dict | None = None,
) -> str:
    analysis_context = analysis_context or {}
    fx_data = analysis_context.get("fx_data")
    gold_data = analysis_context.get("gold_data")
    dealer_spreads = analysis_context.get("dealer_spreads")

    gap_pct = None
    gap_vnd = None
    if current_gap:
        gap_pct = current_gap.get("gap_pct")
        gap_vnd = current_gap.get("gap_vnd")
    if gap_pct is None:
        gap_pct = signal.gap_pct
    if gap_vnd is None:
        gap_vnd = signal.gap_vnd

    if gap_pct is None:
        mode_prefix = _mode_prefix(signal.mode)
        base = "Insufficient data for signal analysis"
        return f"{mode_prefix} {base}" if mode_prefix else base

    ma_value = _find_ma(historical_gaps)
    ma_label, ma_display = _format_ma(ma_value)

    sections: list[str] = []
    sections.append(_build_gap_section(signal, gap_pct, gap_vnd, ma_label, ma_display))
    sections.append(_build_fx_section(fx_data))
    sections.append(_build_gold_section(gold_data))
    sections.append(_build_spread_section(dealer_spreads))
    sections.append(_build_gap_trend_section(historical_gaps))

    seasonal_text = _build_seasonal_context(seasonal_info)
    if seasonal_text:
        sections.append(seasonal_text)

    policy_text = _build_policy_context(policy_info)
    if policy_text:
        sections.append(policy_text)

    sections.append(_build_conclusion(signal))

    combined = "\n".join(s for s in sections if s)
    mode_prefix = _mode_prefix(signal.mode)
    if mode_prefix:
        return f"{mode_prefix}\n{combined}"
    return combined


def _mode_prefix(mode: SignalMode) -> str:
    return {
        SignalMode.SAVER: "For long-term accumulation:",
        SignalMode.TRADER: "For timing-precision:",
    }.get(mode, "")


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


def _build_gap_section(
    signal: Signal,
    gap_pct: float,
    gap_vnd: float | None,
    ma_label: str,
    ma_display: str,
) -> str:
    gap_str = f"{gap_pct:.1f}%"
    rec = signal.recommendation

    lines = [f"Gap: {gap_str}"]

    if gap_vnd is not None:
        lines[0] += f" ({gap_vnd:,.0f} VND)"

    if ma_display:
        deviation = gap_pct - float(ma_display.replace("%", ""))
        direction = "above" if deviation > 0 else "below"
        lines.append(
            f"  vs {ma_label} {ma_display} — {abs(deviation):.1f}pp {direction} average"
        )

    if rec == "BUY":
        lines.append(
            "  Gap widens beyond average — domestic premium rising, potential entry point"
        )
    elif rec == "SELL":
        lines.append(
            "  Gap narrows below average — premium shrinking, favorable to sell domestic"
        )
    else:
        lines.append("  Gap near average — no strong directional signal from gap alone")

    return "\n".join(lines)


def _build_fx_section(fx_data: dict | None) -> str:
    if fx_data is None:
        return ""

    rate = fx_data.get("current_rate")
    trend = fx_data.get("trend", "neutral")
    change_pct = fx_data.get("change_pct", 0)

    if rate is None:
        return ""

    lines = [f"USD/VND: {rate:,.0f}"]

    if trend == "up":
        lines.append(
            f"  VND weakening by {abs(change_pct):.2f}% vs MA — imported gold becomes more expensive, supports wider gap"
        )
    elif trend == "down":
        lines.append(
            f"  VND strengthening by {abs(change_pct):.2f}% vs MA — imported gold cheaper in VND, narrows gap"
        )
    else:
        lines.append(
            f"  Stable (change {change_pct:+.2f}% vs MA) — FX not a major gap driver currently"
        )

    return "\n".join(lines)


def _build_gold_section(gold_data: dict | None) -> str:
    if gold_data is None:
        return ""

    price = gold_data.get("current_price")
    trend = gold_data.get("trend", "neutral")
    momentum = gold_data.get("momentum", 0)

    if price is None:
        return ""

    lines = [f"XAU/USD: ${price:,.2f}/oz"]

    if trend == "up":
        lines.append(
            f"  Gold trending up (+{abs(momentum):.2f}% vs MA) — if domestic price lags, gap widens (buy signal)"
        )
    elif trend == "down":
        lines.append(
            f"  Gold trending down ({momentum:.2f}% vs MA) — if domestic price lags, gap narrows (sell signal)"
        )
    else:
        lines.append(
            f"  Sideways (change {momentum:+.2f}% vs MA) — global gold stable, gap driven by local factors"
        )

    return "\n".join(lines)


def _build_spread_section(dealer_spreads: list[float] | None) -> str:
    if not dealer_spreads:
        return ""

    from statistics import mean

    avg = mean(dealer_spreads)
    lines = [f"Dealer spread: {avg:.2f}%"]

    if avg < 0.5:
        lines.append("  Tight spread — low transaction cost, favorable for trading")
    elif avg < 1.5:
        lines.append("  Normal spread — standard transaction cost")
    else:
        lines.append(
            "  Wide spread — high transaction cost, unfavorable for short-term trading"
        )

    return "\n".join(lines)


def _build_gap_trend_section(historical_gaps: list[dict] | None) -> str:
    if not historical_gaps or len(historical_gaps) < 7:
        return ""

    recent = [
        g["gap_pct"] for g in historical_gaps[-7:] if g.get("gap_pct") is not None
    ]
    older = [g["gap_pct"] for g in historical_gaps[:7] if g.get("gap_pct") is not None]

    if len(recent) < 3 or len(older) < 3:
        return ""

    from statistics import mean

    recent_avg = mean(recent)
    older_avg = mean(older)
    diff = recent_avg - older_avg

    if abs(diff) < 0.5:
        return f"Gap trend: Stable (recent avg {recent_avg:.1f}% vs earlier {older_avg:.1f}%)"

    direction = "widening" if diff > 0 else "narrowing"
    return f"Gap trend: {direction} (recent avg {recent_avg:.1f}% vs earlier {older_avg:.1f}%, {abs(diff):.1f}pp)"


def _build_seasonal_context(seasonal_info: dict | None) -> str:
    if not seasonal_info:
        return ""
    demand_level = seasonal_info.get("demand_level", "")
    month = seasonal_info.get("month", 0)
    if demand_level in ("very_high", "high"):
        from src.engine.seasonal import get_month_name

        month_name = get_month_name(month) if month else ""
        if demand_level == "very_high":
            return f"Seasonal: High demand ({month_name}) — wider gaps typical, adds buy pressure"
        return f"Seasonal: Elevated demand ({month_name}) — wider gaps expected"
    return ""


def _build_policy_context(policy_info: dict | None) -> str:
    if not policy_info or not policy_info.get("has_override"):
        return ""
    summary = policy_info.get("summary", "State Bank policy event active")
    return f"Policy: {summary} — this overrides other signals"


def _build_conclusion(signal: Signal) -> str:
    rec = signal.recommendation
    confidence = signal.confidence

    factors = signal.factors
    bullish = [f.name for f in factors if f.direction > 0 and f.confidence > 0.3]
    bearish = [f.name for f in factors if f.direction < 0 and f.confidence > 0.3]

    factor_names = {
        "gap": "gap premium",
        "spread": "dealer spread",
        "trend": "gap trend",
        "fx_trend": "FX rate",
        "gold_trend": "gold trend",
    }

    bullish_labels = [factor_names.get(n, n) for n in bullish]
    bearish_labels = [factor_names.get(n, n) for n in bearish]

    if rec == "BUY":
        support = ", ".join(bullish_labels) if bullish_labels else "gap analysis"
        line = f"=> BUY (confidence {confidence}%) — supported by {support}"
        if bearish_labels:
            line += f", tempered by {', '.join(bearish_labels)}"
    elif rec == "SELL":
        pressure = ", ".join(bearish_labels) if bearish_labels else "gap analysis"
        line = f"=> SELL (confidence {confidence}%) — pressured by {pressure}"
        if bullish_labels:
            line += f", partially offset by {', '.join(bullish_labels)}"
    else:
        line = f"=> HOLD (confidence {confidence}%) — mixed signals"
        if bullish_labels:
            line += f", bullish: {', '.join(bullish_labels)}"
        if bearish_labels:
            line += f", bearish: {', '.join(bearish_labels)}"

    return line
