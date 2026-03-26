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
    local_data = analysis_context.get("local_data")

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
        base = "Insufficient data for signal analysis (VN: Không đủ dữ liệu để phân tích tín hiệu)"
        return f"{mode_prefix} {base}" if mode_prefix else base

    ma_value = _find_ma(historical_gaps)
    ma_label, ma_display = _format_ma(ma_value)

    sections: list[str] = []
    sections.append(_build_gap_section(signal, gap_pct, gap_vnd, ma_label, ma_display))
    sections.append(_build_fx_section(fx_data))
    sections.append(_build_gold_section(gold_data))
    sections.append(_build_spread_section(dealer_spreads))
    sections.append(_build_local_spread_section(local_data, dealer_spreads))
    sections.append(_build_local_trend_section(local_data))
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
        SignalMode.SAVER: "For long-term accumulation (VN: Dành cho tích lũy dài hạn):",
        SignalMode.TRADER: "For timing-precision (VN: Dành cho thời điểm giao dịch):",
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
        direction_en = "above" if deviation > 0 else "below"
        direction_vn = "cao hơn" if deviation > 0 else "thấp hơn"
        lines.append(
            f"  vs {ma_label} {ma_display} — {abs(deviation):.1f}pp {direction_en} average "
            f"(VN: so với {ma_label} {ma_display} — {abs(deviation):.1f}pp {direction_vn} trung bình)"
        )

    if rec == "BUY":
        lines.append(
            "  Gap widens beyond average — domestic premium rising, potential entry point "
            "(VN: Chênh lệch mở rộng hơn trung bình — giá nội địa tăng, có thể là điểm mua vào)"
        )
    elif rec == "SELL":
        lines.append(
            "  Gap narrows below average — premium shrinking, favorable to sell domestic "
            "(VN: Chênh lệch thu hẹp dưới trung bình — phần bù giảm, thuận lợi để bán vàng nội địa)"
        )
    else:
        lines.append(
            "  Gap near average — no strong directional signal from gap alone "
            "(VN: Chênh lệch gần trung bình — không có tín hiệu rõ ràng từ chênh lệch)"
        )

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
            f"  VND weakening by {abs(change_pct):.2f}% vs MA — imported gold becomes more expensive, supports wider gap "
            f"(VN: VNĐ suy yếu {abs(change_pct):.2f}% so với MA — vàng nhập khẩu đắt hơn, hỗ trợ chênh lệch mở rộng)"
        )
    elif trend == "down":
        lines.append(
            f"  VND strengthening by {abs(change_pct):.2f}% vs MA — imported gold cheaper in VND, narrows gap "
            f"(VN: VNĐ tăng giá {abs(change_pct):.2f}% so với MA — vàng nhập khẩu rẻ hơn, chênh lệch thu hẹp)"
        )
    else:
        lines.append(
            f"  Stable (change {change_pct:+.2f}% vs MA) — FX not a major gap driver currently "
            f"(VN: Ổn định (thay đổi {change_pct:+.2f}% so với MA) — tỷ giá không phải yếu tố chính)"
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
            f"  Gold trending up (+{abs(momentum):.2f}% vs MA) — if domestic price lags, gap widens (buy signal) "
            f"(VN: Vàng tăng (+{abs(momentum):.2f}% so với MA) — nếu giá nội địa chậm, chênh lệch mở rộng (tín hiệu mua)"
        )
    elif trend == "down":
        lines.append(
            f"  Gold trending down ({momentum:.2f}% vs MA) — if domestic price lags, gap narrows (sell signal) "
            f"(VN: Vàng giảm ({momentum:.2f}% so với MA) — nếu giá nội địa chậm, chênh lệch thu hẹp (tín hiệu bán)"
        )
    else:
        lines.append(
            f"  Sideways (change {momentum:+.2f}% vs MA) — global gold stable, gap driven by local factors "
            f"(VN: Đi ngang (thay đổi {momentum:+.2f}% so với MA) — vàng thế giới ổn định, chênh lệch do yếu tố nội địa)"
        )

    return "\n".join(lines)


def _build_spread_section(dealer_spreads: list[float] | None) -> str:
    if not dealer_spreads:
        return ""

    from statistics import mean

    avg = mean(dealer_spreads)
    lines = [f"Dealer spread: {avg:.2f}%"]

    if avg < 0.5:
        lines.append(
            "  Tight spread — low transaction cost, favorable for trading "
            "(VN: Chênh lệch hẹp — chi phí giao dịch thấp, thuận lợi giao dịch)"
        )
    elif avg < 1.5:
        lines.append(
            "  Normal spread — standard transaction cost "
            "(VN: Chênh lệch bình thường — chi phí giao dịch tiêu chuẩn)"
        )
    else:
        lines.append(
            "  Wide spread — high transaction cost, unfavorable for short-term trading "
            "(VN: Chênh lệch rộng — chi phí giao dịch cao, bất lợi cho giao dịch ngắn hạn)"
        )

    return "\n".join(lines)


def _build_local_spread_section(
    local_data: dict | None, dealer_spreads: list[float] | None
) -> str:
    if not local_data:
        return ""

    spread_pct = local_data.get("spread_pct")
    if spread_pct is None:
        return ""

    from statistics import mean

    lines = [f"Local store spread: {spread_pct:.2f}%"]

    if dealer_spreads:
        avg_dealer = mean(dealer_spreads)
        diff = spread_pct - avg_dealer
        lines.append(f"  Dealer avg: {avg_dealer:.2f}%")
        if diff < -0.5:
            lines.append(
                "  Your store has a tighter spread than dealers — favorable for trading "
                "(VN: Tiệm của bạn có chênh lệch hẹp hơn đại lý — thuận lợi giao dịch)"
            )
        elif diff <= 0.5:
            lines.append(
                "  Similar to dealer spreads — normal transaction cost "
                "(VN: Tương tự đại lý — chi phí giao dịch bình thường)"
            )
        elif diff <= 1.5:
            lines.append(
                "  Slightly wider than dealers — moderate extra cost per trade "
                "(VN: Hơi rộng hơn đại lý — chi phí thêm mỗi giao dịch ở mức vừa)"
            )
        else:
            lines.append(
                "  Significantly wider than dealers — high transaction cost, factor into timing "
                "(VN: Rộng hơn đáng kể so với đại lý — chi phí giao dịch cao, cần tính toán thời điểm)"
            )
    else:
        if spread_pct < 1.5:
            lines.append(
                "  Tight spread — low transaction cost "
                "(VN: Chênh lệch hẹp — chi phí giao dịch thấp)"
            )
        elif spread_pct < 3.0:
            lines.append(
                "  Normal spread — standard transaction cost "
                "(VN: Chênh lệch bình thường — chi phí giao dịch tiêu chuẩn)"
            )
        else:
            lines.append(
                "  Wide spread — high transaction cost, trade less frequently "
                "(VN: Chênh lệch rộng — chi phí giao dịch cao, hạn chế giao dịch)"
            )

    return "\n".join(lines)


def _build_local_trend_section(local_data: dict | None) -> str:
    if not local_data:
        return ""

    trend_7d = local_data.get("trend_7d")
    trend_30d = local_data.get("trend_30d")

    if trend_7d is None:
        return ""

    lines = [f"Local ring gold 7d trend: {trend_7d:+.2f}%"]

    if trend_30d is not None:
        lines[0] += f" (30d: {trend_30d:+.2f}%)"
        if (trend_7d < 0 and trend_30d < 0) or (trend_7d > 0 and trend_30d > 0):
            lines.append(
                "  7d and 30d trends agree — directional confidence higher "
                "(VN: Xu hướng 7 ngày và 30 ngày đồng pha — độ tin cậy cao hơn)"
            )
        else:
            lines.append(
                "  7d and 30d trends diverge — recent move may be short-term "
                "(VN: Xu hướng 7 ngày và 30 ngày khác nhau — biến động gần đây có thể ngắn hạn)"
            )

    if trend_7d < -1.0:
        lines.append(
            "  Prices falling — favorable for buying "
            "(VN: Giá giảm — thuận lợi để mua vào)"
        )
    elif trend_7d < 0:
        lines.append(
            "  Prices slightly declining — mild buy signal "
            "(VN: Giá giảm nhẹ — tín hiệu mua yếu)"
        )
    elif trend_7d <= 1.0:
        lines.append(
            "  Prices stable — no timing advantage from trend "
            "(VN: Giá ổn định — không có lợi thế thời điểm từ xu hướng)"
        )
    else:
        lines.append(
            "  Prices rising — consider waiting or selling "
            "(VN: Giá tăng — cân nhắc chờ hoặc bán ra)"
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
        return (
            f"Gap trend: Stable (recent avg {recent_avg:.1f}% vs earlier {older_avg:.1f}%) "
            f"(VN: Xu hướng chênh lệch: Ổn định (TB gần {recent_avg:.1f}% so với trước {older_avg:.1f}%))"
        )

    direction_en = "widening" if diff > 0 else "narrowing"
    direction_vn = "mở rộng" if diff > 0 else "thu hẹp"
    return (
        f"Gap trend: {direction_en} (recent avg {recent_avg:.1f}% vs earlier {older_avg:.1f}%, {abs(diff):.1f}pp) "
        f"(VN: Xu hướng chênh lệch: {direction_vn} (TB gần {recent_avg:.1f}% so với trước {older_avg:.1f}%, {abs(diff):.1f}pp))"
    )


def _build_seasonal_context(seasonal_info: dict | None) -> str:
    if not seasonal_info:
        return ""
    demand_level = seasonal_info.get("demand_level", "")
    month = seasonal_info.get("month", 0)
    if demand_level in ("very_high", "high"):
        from src.engine.seasonal import get_month_name

        month_name = get_month_name(month) if month else ""
        if demand_level == "very_high":
            return (
                f"Seasonal: High demand ({month_name}) — wider gaps typical, adds buy pressure "
                f"(VN: Mùa vụ: Nhu cầu cao ({month_name}) — chênh lệch rộng thường gặp, tăng áp lực mua)"
            )
        return (
            f"Seasonal: Elevated demand ({month_name}) — wider gaps expected "
            f"(VN: Mùa vụ: Nhu cầu tăng ({month_name}) — chênh lệch có thể mở rộng)"
        )
    return ""


def _build_policy_context(policy_info: dict | None) -> str:
    if not policy_info or not policy_info.get("has_override"):
        return ""
    summary = policy_info.get("summary", "State Bank policy event active")
    return (
        f"Policy: {summary} — this overrides other signals "
        f"(VN: Chính sách: {summary} — ưu tiên hơn các tín hiệu khác)"
    )


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
        "local_spread": "local store spread",
        "local_trend": "local price trend",
    }

    factor_names_vn = {
        "gap": "chênh lệch giá",
        "spread": "chênh lệch đại lý",
        "trend": "xu hướng chênh lệch",
        "fx_trend": "tỷ giá USD/VNĐ",
        "gold_trend": "xu hướng vàng thế giới",
        "local_spread": "chênh lệch tiệm vàng",
        "local_trend": "xu hướng giá tiệm vàng",
    }

    bullish_labels = [factor_names.get(n, n) for n in bullish]
    bearish_labels = [factor_names.get(n, n) for n in bearish]
    bullish_labels_vn = [factor_names_vn.get(n, n) for n in bullish]
    bearish_labels_vn = [factor_names_vn.get(n, n) for n in bearish]

    if rec == "BUY":
        support = ", ".join(bullish_labels) if bullish_labels else "gap analysis"
        support_vn = (
            ", ".join(bullish_labels_vn)
            if bullish_labels_vn
            else "phân tích chênh lệch"
        )
        line = f"=> BUY (confidence {confidence}%) — supported by {support} (VN: MUA (độ tin cậy {confidence}%) — được hỗ trợ bởi {support_vn})"
        if bearish_labels:
            tempered = ", ".join(bearish_labels)
            tempered_vn = ", ".join(bearish_labels_vn)
            line += f", tempered by {tempered} (VN: bù trừ bởi {tempered_vn})"
    elif rec == "SELL":
        pressure = ", ".join(bearish_labels) if bearish_labels else "gap analysis"
        pressure_vn = (
            ", ".join(bearish_labels_vn)
            if bearish_labels_vn
            else "phân tích chênh lệch"
        )
        line = f"=> SELL (confidence {confidence}%) — pressured by {pressure} (VN: BÁN (độ tin cậy {confidence}%) — chịu áp lực từ {pressure_vn})"
        if bullish_labels:
            offset = ", ".join(bullish_labels)
            offset_vn = ", ".join(bullish_labels_vn)
            line += (
                f", partially offset by {offset} (VN: bù trừ một phần bởi {offset_vn})"
            )
    else:
        bullish_str = ", ".join(bullish_labels) if bullish_labels else ""
        bearish_str = ", ".join(bearish_labels) if bearish_labels else ""
        bullish_str_vn = ", ".join(bullish_labels_vn) if bullish_labels_vn else ""
        bearish_str_vn = ", ".join(bearish_labels_vn) if bearish_labels_vn else ""
        line = f"=> HOLD (confidence {confidence}%) — mixed signals (VN: GIỮ (độ tin cậy {confidence}%) — tín hiệu lẫn lộn)"
        if bullish_labels:
            line += f", bullish: {bullish_str} (VN: tăng giá: {bullish_str_vn})"
        if bearish_labels:
            line += f", bearish: {bearish_str} (VN: giảm giá: {bearish_str_vn})"

    return line
