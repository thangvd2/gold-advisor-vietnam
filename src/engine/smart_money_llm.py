"""LLM-powered smart money signal explanations via GLM-5-turbo structured output.

Generates bilingual (EN + VN) explanations for Polymarket smart money signals:
  - what_happened: Description of the market move
  - why_significant: Why this move is notable
  - gold_implication: How this relates to gold (if applicable)

Uses OpenAI SDK with Z.ai endpoint and 10-minute TTL cache.
Falls back gracefully — returns None on any error.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from src.config import Settings

if TYPE_CHECKING:
    from src.storage.models import PolymarketSmartSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Structured output models
# ---------------------------------------------------------------------------


class SmartMoneyExplanation(BaseModel):
    """LLM-generated explanation for a smart money signal."""

    what_happened: dict[str, str]  # {"en": "...", "vn": "..."}
    why_significant: dict[str, str]  # {"en": "...", "vn": "..."}
    gold_implication: dict[str, str] | None = None  # {"en": "...", "vn": "..."} or null


# ---------------------------------------------------------------------------
# Cache
# ---------------------------------------------------------------------------

_cache: dict[int, tuple[float, SmartMoneyExplanation | None]] = {}
_CACHE_TTL = 600  # 10 minutes


def _cache_key(signal_id: int) -> int:
    return signal_id


def _get_cached(signal_id: int) -> SmartMoneyExplanation | None:
    entry = _cache.get(_cache_key(signal_id))
    if entry is None:
        return None
    ts, explanation = entry
    if time.monotonic() - ts > _CACHE_TTL:
        del _cache[_cache_key(signal_id)]
        return None
    return explanation


def _set_cached(signal_id: int, explanation: SmartMoneyExplanation | None) -> None:
    _cache[_cache_key(signal_id)] = (time.monotonic(), explanation)


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
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """\
You are a prediction market analyst specializing in Polymarket data. You produce \
clear, bilingual explanations (English + Vietnamese) for smart money signals \
detected in prediction market movements.

## Context
You analyze significant price moves in Polymarket events that may indicate \
informed trading activity (smart money). Your job is to explain these moves \
in simple terms for Vietnamese gold investors.

## Rules
1. Use OBSERVATIONAL language ("market data suggests", "betting patterns show", \
"prices indicate"). Never say "will", "expected to", "predicts", or "likely to".
2. Be specific — cite exact price move, direction, and magnitude from the data.
3. Explain WHY the move is notable:
   - Does it contradict recent news narrative?
   - Is there no obvious news explanation?
   - Did trading volume spike?
4. If the event relates to gold, FX, Fed policy, or macro economics, explain \
the potential gold price implication.
5. Each explanation section should be 2-4 sentences per language. Be concise.
6. Vietnamese text MUST use proper diacritical marks (dấu). Required marks:
   - ơ, ư (sắc, huyền, hỏi, ngã, nặng)
   - à, ả, ã, á, ạ, À, Ả, Ã, Á, Ạ
   - é, è, ẹ, ẽ, ê, ề, ể, ễ, ệ
   - í, ì, ỉ, ĩ, ị
   - ó, ò, ỏ, õ, ọ, ô, ồ, ổ, ỗ, ộ, ơ, ờ, ở, ỡ, ợ
   - ú, ù, ủ, ũ, ụ, ư, ừ, ử, ữ, ự
   - ý, ỳ, ỷ, ỹ, ỵ
   - đ, Đ
   Examples: "chênh lệch", "tăng", "giảm", "định giá", "thị trường", "dòng tiền", \
"thông minh", "biến động", "phân tích", "dự đoán", "nghịch lý".
7. If data is insufficient, say so explicitly in the explanation.
8. The gold_implication field is OPTIONAL — only include if the event clearly \
relates to gold, FX, Fed policy, or macro economics.

## Output Format
You MUST return valid JSON with EXACTLY these top-level keys:
- what_happened: object with "en" and "vn" string fields
- why_significant: object with "en" and "vn" string fields  
- gold_implication: object with "en" and "vn" string fields (omit if not relevant)

Example output:
{
  "what_happened": {
    "en": "The probability jumped from 45¢ to 62¢ in 4 hours...",
    "vn": "Xác suất tăng từ 45 xu lên 62 xu trong 4 giờ..."
  },
  "why_significant": {
    "en": "This move contradicts the bearish news narrative...",
    "vn": "Biến động này trái ngược với tin tức tiêu cực..."
  },
  "gold_implication": {
    "en": "If this Fed-related event materializes, gold prices may...",
    "vn": "Nếu sự kiện liên quan đến Fed này xảy ra, giá vàng có thể..."
  }
}

Do NOT wrap the response in any other field. Return the JSON object directly.
If gold_implication is not relevant, omit it entirely.
"""


# ---------------------------------------------------------------------------
# Data payload builder
# ---------------------------------------------------------------------------


def _build_signal_payload(
    signal: PolymarketSmartSignal,
    related_news: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the JSON payload fed to GLM-5-turbo."""
    payload: dict[str, Any] = {
        "title": signal.title,
        "slug": signal.slug,
        "category": signal.category,
        "signal_type": signal.signal_type,
        "price_before": signal.price_before,
        "price_after": signal.price_after,
        "move_cents": signal.move_cents,
        "move_direction": signal.move_direction,
        "confidence": round(signal.confidence, 2),
        "news_count_4h": signal.news_count_4h,
        "news_consensus": signal.news_consensus,
    }

    if related_news:
        payload["related_news"] = [
            {"headline": n.get("headline", n.get("title", ""))}
            for n in related_news[:5]  # Limit to 5 headlines
        ]

    return payload


# ---------------------------------------------------------------------------
# LLM caller
# ---------------------------------------------------------------------------


async def generate_smart_money_explanation(
    signal: PolymarketSmartSignal,
    related_news: list[dict[str, Any]] | None = None,
) -> SmartMoneyExplanation | None:
    """Generate an LLM-powered bilingual explanation for a smart money signal.

    Returns None on any error (API unavailable, parse failure, etc.).
    Results are cached for 10 minutes per signal ID.
    """
    cached = _get_cached(signal.id)
    if cached is not None:
        return cached

    api_key = _resolve_api_key()
    if not api_key:
        logger.debug("No API key — skipping smart money LLM explanation")
        _set_cached(signal.id, None)
        return None

    settings = Settings()

    payload = _build_signal_payload(signal, related_news)

    user_message = (
        "Analyze the smart money signal below and return a JSON object with these "
        "exact keys: what_happened, why_significant. Optionally include "
        "gold_implication if relevant to gold/FX/Fed policy. "
        'Each key maps to {"en": "...", "vn": "..."}.\n\n'
        f"```json\n{json.dumps(payload, indent=2, ensure_ascii=False)}\n```"
    )

    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(
            api_key=api_key,
            base_url=settings.openai_base_url,
        )

        response = await client.chat.completions.create(
            model=settings.openai_model_name,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.5,
            max_tokens=2048,
        )

        content = response.choices[0].message.content
        if not content:
            logger.warning("LLM returned empty content for smart money signal")
            _set_cached(signal.id, None)
            return None

        data = json.loads(content)

        # Validate required fields with .get() defaults
        what_happened = data.get("what_happened", {})
        why_significant = data.get("why_significant", {})
        gold_implication = data.get("gold_implication")

        if not what_happened.get("en") or not what_happened.get("vn"):
            logger.warning("LLM missing what_happened fields")
            _set_cached(signal.id, None)
            return None

        if not why_significant.get("en") or not why_significant.get("vn"):
            logger.warning("LLM missing why_significant fields")
            _set_cached(signal.id, None)
            return None

        explanation = SmartMoneyExplanation(
            what_happened={
                "en": what_happened.get("en", ""),
                "vn": what_happened.get("vn", ""),
            },
            why_significant={
                "en": why_significant.get("en", ""),
                "vn": why_significant.get("vn", ""),
            },
            gold_implication=(
                {
                    "en": gold_implication.get("en", ""),
                    "vn": gold_implication.get("vn", ""),
                }
                if gold_implication
                else None
            ),
        )

        _set_cached(signal.id, explanation)
        logger.info("Smart money LLM explanation generated for signal_id=%s", signal.id)
        return explanation

    except Exception:
        logger.warning("Smart money LLM explanation failed", exc_info=True)
        _set_cached(signal.id, None)
        return None
