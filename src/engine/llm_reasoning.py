"""LLM-powered signal reasoning via GLM-5-turbo structured output.

Generates bilingual (EN + VN) explanations for the gold signal:
  - Compact reasoning for the signal card
  - Detailed per-section explanations for the full report page

Uses OpenAI SDK with Z.ai endpoint and 5-minute TTL cache.
Falls back gracefully — returns None on any error.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any

from pydantic import BaseModel, Field

from src.config import Settings
from src.engine.types import Signal, SignalMode

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------


class BilingualText(BaseModel):
    """A single piece of text in both English and Vietnamese."""

    en: str
    vn: str


class SignalReport(BaseModel):
    """Full LLM-generated report with bilingual explanations for every section."""

    compact_reasoning: BilingualText = Field(
        description="2-3 sentence summary of the overall signal. Mention the recommendation, "
        "key driving factors, and any caveats. Be specific with numbers."
    )
    gap_analysis: BilingualText = Field(
        description="Detailed explanation of the domestic-international gap. "
        "Interpret what the current gap level means vs historical averages."
    )
    fx_analysis: BilingualText = Field(
        description="Explanation of the USD/VND rate and its impact on gold prices."
    )
    gold_analysis: BilingualText = Field(
        description="Explanation of international gold price (XAU/USD) movement."
    )
    dealer_spread_analysis: BilingualText = Field(
        description="Analysis of dealer buy-sell spread and what it means for liquidity."
    )
    local_store_analysis: BilingualText = Field(
        description="Analysis of the local gold store prices, spread vs dealers, and price trends. "
        "This is where the user actually trades ring gold."
    )
    gap_trend_analysis: BilingualText = Field(
        description="Whether the gap is widening or narrowing over time and what it implies."
    )
    seasonal_context: BilingualText = Field(
        description="Current seasonal demand level and its influence on prices."
    )
    policy_context: BilingualText | None = Field(
        default=None,
        description="Policy alert if State Bank override is active. Null if no active policy.",
    )
    conclusion: BilingualText = Field(
        description="Final recommendation summary. List which factors support and which oppose "
        "the recommendation. Reiterate the confidence level."
    )


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[float, SignalReport | None]] = {}
_CACHE_TTL = 300  # 5 minutes


def _cache_key(mode: SignalMode) -> str:
    return f"llm_report_{mode.value}"


def _get_cached(mode: SignalMode) -> SignalReport | None:
    entry = _cache.get(_cache_key(mode))
    if entry is None:
        return None
    ts, report = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _cache[_cache_key(mode)]
        return None
    return report


def _set_cached(mode: SignalMode, report: SignalReport | None) -> None:
    _cache[_cache_key(mode)] = (time.monotonic(), report)


# ---------------------------------------------------------------------------
# API key resolution
# ---------------------------------------------------------------------------


def _resolve_api_key() -> str:
    settings = Settings()
    if settings.openai_api_key:
        return settings.openai_api_key
    for path in [".glm_key", os.path.expanduser("~/.glm_key")]:
        if os.path.isfile(path):
            try:
                with open(path) as f:
                    key = f.read().strip()
                if key:
                    return key
            except OSError:
                pass
    return ""


# ---------------------------------------------------------------------------
# Data payload builder
# ---------------------------------------------------------------------------


def build_data_payload(
    signal: Signal,
    current_gap: dict[str, Any] | None = None,
    historical_gaps: list[dict[str, Any]] | None = None,
    dealer_spreads: list[float] | None = None,
    local_data: dict[str, Any] | None = None,
    fx_data: dict[str, Any] | None = None,
    gold_data: dict[str, Any] | None = None,
    seasonal_info: dict[str, Any] | None = None,
    policy_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the JSON payload fed to GLM-5-turbo."""
    from statistics import mean

    payload: dict[str, Any] = {
        "recommendation": signal.recommendation.value,
        "confidence": signal.confidence,
        "mode": signal.mode.value,
        "factors": [
            {
                "name": f.name,
                "direction": round(f.direction, 3),
                "weight": round(f.weight, 3),
                "confidence": round(f.confidence, 3),
                "impact": round(f.direction * f.weight, 3),
            }
            for f in signal.factors
        ],
    }

    if current_gap:
        payload["gap"] = {
            "gap_pct": round(current_gap.get("gap_pct", 0), 2)
            if current_gap.get("gap_pct") is not None
            else None,
            "gap_vnd": current_gap.get("gap_vnd"),
            "avg_sjc_sell_vnd": current_gap.get("avg_sjc_sell"),
            "intl_price_vnd": current_gap.get("intl_price_vnd"),
            "intl_price_usd": current_gap.get("intl_price_usd"),
        }

    if historical_gaps:
        valid = [g for g in historical_gaps if g.get("gap_pct") is not None]
        last = valid[-1] if valid else {}
        recent = valid[-7:] if len(valid) >= 7 else valid
        older = valid[:7] if len(valid) >= 7 else valid

        recent_avg = mean(g["gap_pct"] for g in recent) if recent else None
        older_avg = mean(g["gap_pct"] for g in older) if older else None

        payload["gap_history"] = {
            "latest_ma_7d": last.get("ma_7d"),
            "latest_ma_30d": last.get("ma_30d"),
            "recent_7d_avg": round(recent_avg, 2) if recent_avg else None,
            "older_avg": round(older_avg, 2) if older_avg else None,
            "trend": (
                "widening"
                if recent_avg and older_avg and recent_avg > older_avg + 0.5
                else (
                    "narrowing"
                    if recent_avg and older_avg and recent_avg < older_avg - 0.5
                    else "stable"
                )
            ),
            "data_points": len(valid),
        }

    if dealer_spreads:
        payload["dealer_spreads"] = {
            "average": round(mean(dealer_spreads), 2),
            "min": round(min(dealer_spreads), 2),
            "max": round(max(dealer_spreads), 2),
            "count": len(dealer_spreads),
        }

    if local_data:
        ld: dict[str, Any] = {}
        if local_data.get("latest_buy") is not None:
            ld["buy_price_vnd"] = local_data["latest_buy"]
        if local_data.get("latest_sell") is not None:
            ld["sell_price_vnd"] = local_data["latest_sell"]
        if local_data.get("spread_pct") is not None:
            ld["spread_pct"] = round(local_data["spread_pct"], 2)
        if local_data.get("trend_7d") is not None:
            ld["trend_7d_pct"] = round(local_data["trend_7d"], 2)
        if local_data.get("trend_30d") is not None:
            ld["trend_30d_pct"] = round(local_data["trend_30d"], 2)
        ld["data_points"] = local_data.get("data_points", 0)
        payload["local_store"] = ld

    if fx_data:
        payload["fx_rate"] = {
            "current_rate": fx_data.get("current_rate"),
            "trend": fx_data.get("trend", "neutral"),
            "change_pct_vs_ma": round(fx_data.get("change_pct", 0), 2),
        }

    if gold_data:
        payload["gold_price"] = {
            "current_usd_per_oz": gold_data.get("current_price"),
            "trend": gold_data.get("trend", "neutral"),
            "momentum_pct": round(gold_data.get("momentum", 0), 2),
        }

    if seasonal_info:
        payload["seasonal"] = {
            "month": seasonal_info.get("month"),
            "demand_level": seasonal_info.get("demand_level", "unknown"),
        }

    if policy_info:
        payload["policy"] = {
            "has_override": policy_info.get("has_override", False),
            "summary": policy_info.get("summary"),
        }

    return payload


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a gold market analyst for Gold Advisor Vietnam. You produce clear, \
bilingual explanations (English + Vietnamese) for gold trading signals.

## Context
The user ONLY buys and sells ring gold (nhẫn trơn) at a single local store \
called "Tiệm vàng gần nhà" — NOT SJC bars, NOT other dealers. Every analysis \
you write must be framed around helping the user decide whether to BUY, SELL, \
or HOLD ring gold at that specific store. The gold signal, compact explanation, \
and full detailed report all serve this single purpose.

## Rules
1. Use OBSERVATIONAL language ("tracks", "analyzes", "shows"). Never PREDICT. \
Never say "will", "expected to", or "likely to".
2. Be specific with numbers from the data. Don't be vague.
3. Vietnamese text MUST use proper diacritical marks (dấu). Example: "chênh lệch", \
"tăng", "giảm", "định giá", "thị trường", "yếu tố".
4. Each explanation should be 2-4 sentences per language. Be concise but informative.
5. Frame every analysis around ring gold at Tiệm vàng gần nhà — that is the \
only store the user trades at. SJC and dealer data provide market context only.
6. If a data field is null/missing, acknowledge the data gap rather than guessing.
7. State Bank of Vietnam policy overrides all other signals — mention this when active.

## Output Format
You MUST return valid JSON with EXACTLY these top-level keys. Each value is \
an object with "en" and "vn" string fields:
- compact_reasoning
- gap_analysis
- fx_analysis
- gold_analysis
- dealer_spread_analysis
- local_store_analysis
- gap_trend_analysis
- seasonal_context
- policy_context (omit if no active policy)
- conclusion

Example: {"compact_reasoning": {"en": "...", "vn": "..."}, ...}
Do NOT wrap the response in any other field. Return the JSON object directly.
"""


# ---------------------------------------------------------------------------
# LLM caller
# ---------------------------------------------------------------------------


async def generate_llm_report(
    signal: Signal,
    current_gap: dict[str, Any] | None = None,
    historical_gaps: list[dict[str, Any]] | None = None,
    dealer_spreads: list[float] | None = None,
    local_data: dict[str, Any] | None = None,
    fx_data: dict[str, Any] | None = None,
    gold_data: dict[str, Any] | None = None,
    seasonal_info: dict[str, Any] | None = None,
    policy_info: dict[str, Any] | None = None,
) -> SignalReport | None:
    """Generate an LLM-powered bilingual signal report.

    Returns None on any error (API unavailable, parse failure, etc.).
    Results are cached for 5 minutes per mode.
    """
    cached = _get_cached(signal.mode)
    if cached is not None:
        return cached

    api_key = _resolve_api_key()
    if not api_key:
        logger.debug("No API key — skipping LLM reasoning")
        _set_cached(signal.mode, None)
        return None

    settings = Settings()

    payload = build_data_payload(
        signal,
        current_gap,
        historical_gaps,
        dealer_spreads,
        local_data,
        fx_data,
        gold_data,
        seasonal_info,
        policy_info,
    )

    user_message = (
        "Analyze the signal data below and return a JSON object with these exact "
        "keys: compact_reasoning, gap_analysis, fx_analysis, gold_analysis, "
        "dealer_spread_analysis, local_store_analysis, gap_trend_analysis, "
        "seasonal_context, policy_context (omit if none), conclusion. "
        'Each key maps to {"en": "...", "vn": "..."}. '
        "Remember: the user only trades ring gold at Tiệm vàng gần nhà.\n\n"
        f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```"
    )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.openai_base_url,
        )

        logger.debug("→ LLM signal report (%s)", settings.openai_model_name)
        response = await client.chat.completions.create(
            model=settings.openai_model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=4096,
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("LLM returned empty content")
            _set_cached(signal.mode, None)
            return None

        data = json.loads(content)

        # Map JSON fields to SignalReport fields
        report = SignalReport(
            compact_reasoning=BilingualText(
                en=data.get("compact_reasoning", {}).get("en", ""),
                vn=data.get("compact_reasoning", {}).get("vn", ""),
            ),
            gap_analysis=BilingualText(
                en=data.get("gap_analysis", {}).get("en", ""),
                vn=data.get("gap_analysis", {}).get("vn", ""),
            ),
            fx_analysis=BilingualText(
                en=data.get("fx_analysis", {}).get("en", ""),
                vn=data.get("fx_analysis", {}).get("vn", ""),
            ),
            gold_analysis=BilingualText(
                en=data.get("gold_analysis", {}).get("en", ""),
                vn=data.get("gold_analysis", {}).get("vn", ""),
            ),
            dealer_spread_analysis=BilingualText(
                en=data.get("dealer_spread_analysis", {}).get("en", ""),
                vn=data.get("dealer_spread_analysis", {}).get("vn", ""),
            ),
            local_store_analysis=BilingualText(
                en=data.get("local_store_analysis", {}).get("en", ""),
                vn=data.get("local_store_analysis", {}).get("vn", ""),
            ),
            gap_trend_analysis=BilingualText(
                en=data.get("gap_trend_analysis", {}).get("en", ""),
                vn=data.get("gap_trend_analysis", {}).get("vn", ""),
            ),
            seasonal_context=BilingualText(
                en=data.get("seasonal_context", {}).get("en", ""),
                vn=data.get("seasonal_context", {}).get("vn", ""),
            ),
            policy_context=(
                BilingualText(
                    en=data.get("policy_context", {}).get("en", ""),
                    vn=data.get("policy_context", {}).get("vn", ""),
                )
                if data.get("policy_context")
                else None
            ),
            conclusion=BilingualText(
                en=data.get("conclusion", {}).get("en", ""),
                vn=data.get("conclusion", {}).get("vn", ""),
            ),
        )

        _set_cached(signal.mode, report)
        logger.info("LLM report generated for mode=%s", signal.mode.value)
        return report

    except Exception:
        logger.exception("LLM report generation failed")
        _set_cached(signal.mode, None)
        return None
