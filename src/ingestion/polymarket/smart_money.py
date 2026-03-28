STOPWORDS = {
    "a",
    "an",
    "the",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "can",
    "shall",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "before",
    "after",
    "above",
    "below",
    "between",
    "under",
    "again",
    "further",
    "then",
    "once",
    "here",
    "there",
    "when",
    "where",
    "why",
    "how",
    "all",
    "both",
    "each",
    "few",
    "more",
    "most",
    "other",
    "some",
    "such",
    "no",
    "nor",
    "not",
    "only",
    "own",
    "same",
    "so",
    "than",
    "too",
    "very",
    "just",
    "because",
    "but",
    "and",
    "or",
    "if",
    "while",
    "about",
    "this",
    "that",
    "these",
    "those",
    "it",
    "its",
    "he",
    "she",
    "they",
    "we",
    "you",
    "i",
    "me",
    "my",
    "your",
    "his",
    "her",
    "our",
    "their",
    "what",
    "which",
    "who",
    "whom",
    "up",
    "down",
    "?",
    "!",
    ".",
    ",",
    ":",
    ";",
    "'",
    '"',
    "-",
    "—",
    "–",
}

DOWN_WORDS = {
    "cut",
    "drop",
    "fall",
    "falls",
    "decline",
    "decrease",
    "crash",
    "plunge",
    "slump",
    "lose",
    "loss",
    "lower",
    "miss",
    "missed",
    "fail",
    "failed",
    "rejection",
    "reject",
    "rejected",
    "ban",
    "banned",
    "block",
    "blocked",
    "delay",
    "delayed",
    "worse",
    "weak",
    "negative",
    "bear",
    "bearish",
    "risk",
    "risks",
    "fear",
    "fears",
    "concern",
    "concerns",
    "slow",
    "slowdown",
    "recession",
    "tariff",
    "war",
    "sanction",
    "inflation",
    "unemployment",
    "debt",
    "deficit",
    "crisis",
    "strike",
    "protest",
    "tension",
    "conflict",
}

UP_WORDS = {
    "rise",
    "rises",
    "gain",
    "gains",
    "increase",
    "surge",
    "jump",
    "soar",
    "rally",
    "bull",
    "bullish",
    "pass",
    "passed",
    "approve",
    "approved",
    "win",
    "won",
    "growth",
    "strong",
    "positive",
    "optimis",
    "boost",
    "recovery",
    "breakthrough",
    "deal",
    "agreement",
    "settle",
    "settled",
    "peace",
    "ceasefire",
    "support",
    "rate cut",
    "rate reduction",
    "hike",
}


def get_move_threshold(liquidity: float | None) -> float:
    if liquidity is None or liquidity < 50000:
        return 5.0
    if liquidity < 250000:
        return 3.0
    return 2.0


def _extract_keywords(title: str) -> set[str]:
    words = title.lower().split()
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def find_related_news(title: str, news_items: list[dict]) -> list[dict]:
    keywords = _extract_keywords(title)
    if not keywords:
        return []

    matched = []
    for item in news_items:
        item_title = item.get("title", "").lower()
        item_excerpt = item.get("excerpt", "").lower()
        combined = item_title + " " + item_excerpt

        if any(kw in combined for kw in keywords):
            matched.append(item)

    return matched


def classify_news_consensus(related_news: list[dict], move_direction: str) -> str:
    if not related_news:
        return "none"

    total_up = 0
    total_down = 0

    for news in related_news:
        text = (news.get("title", "") + " " + news.get("excerpt", "")).lower()

        for word in DOWN_WORDS:
            if word in text:
                total_down += 1

        for word in UP_WORDS:
            if word in text:
                total_up += 1

    if move_direction == "down":
        if total_down > total_up:
            return "supports"
        if total_up > total_down:
            return "contradicts"
    elif move_direction == "up":
        if total_up > total_down:
            return "supports"
        if total_down > total_up:
            return "contradicts"

    return "none"


def build_reasoning(signal: dict) -> tuple[str, str]:
    direction = signal.get("move_direction", "")
    move_cents = signal.get("move_cents", 0)
    news_count = signal.get("news_count_4h", 0)
    signal_type = signal.get("signal_type", "")
    has_volume_spike = signal.get("volume_spike", False)

    direction_vn = "tăng" if direction == "up" else "giảm"
    volume_note = "Volume spike detected (5x+ increase)." if has_volume_spike else ""
    volume_note_vn = (
        "Phát hiện đột biến khối lượng (tăng 5 lần trở lên)."
        if has_volume_spike
        else ""
    )

    if signal_type == "contrarian":
        en = (
            f"Price moved {direction} {move_cents:.1f}¢ while {news_count} "
            f"news article(s) suggested the opposite direction. {volume_note}"
        ).strip()
        vn = (
            f"Giá {direction_vn} {move_cents:.1f}¢ trong khi {news_count} "
            f"bài báo cho xu hướng ngược lại. {volume_note_vn}"
        ).strip()
    else:
        en = (
            f"Price moved {direction} {move_cents:.1f}¢ with no related news "
            f"in the past 4 hours. {volume_note}"
        ).strip()
        vn = (
            f"Giá {direction_vn} {move_cents:.1f}¢ mà không có tin tức liên quan "
            f"trong 4 giờ qua. {volume_note_vn}"
        ).strip()

    return en, vn


def detect_smart_moves(
    new_snapshots: list[dict],
    previous_snapshots: list[dict],
    recent_news: list[dict],
) -> list[dict]:
    signals = []

    prev_by_slug: dict[str, list[dict]] = {}
    for snap in previous_snapshots:
        slug = snap.get("slug")
        if slug:
            prev_by_slug.setdefault(slug, []).append(snap)

    for slug, snaps in prev_by_slug.items():
        prev_by_slug[slug] = sorted(
            snaps, key=lambda x: x.get("fetched_at", ""), reverse=True
        )

    for new in new_snapshots:
        slug = new.get("slug")
        if not slug:
            continue

        prev_list = prev_by_slug.get(slug, [])
        if not prev_list:
            continue

        prev = prev_list[0]

        new_price = new.get("yes_price")
        prev_price = prev.get("yes_price")
        if new_price is None or prev_price is None:
            continue

        move_cents = abs(new_price - prev_price) * 100
        if move_cents == 0:
            continue

        move_direction = "up" if new_price > prev_price else "down"

        threshold = get_move_threshold(new.get("liquidity"))
        if move_cents < threshold:
            continue

        title = new.get("title", "")
        related_news = find_related_news(title, recent_news)
        consensus = classify_news_consensus(related_news, move_direction)

        if consensus == "supports":
            continue

        signal_type = None
        confidence = 0.0

        if consensus == "contradicts":
            signal_type = "contrarian"
            confidence = 0.8
        elif consensus == "none" and move_cents > threshold * 2:
            signal_type = "no_news"
            confidence = 0.5
        else:
            continue

        new_volume = new.get("volume_24h") or 0
        prev_volume = prev.get("volume_24h") or 0
        volume_spike = prev_volume > 0 and new_volume > prev_volume * 5

        if volume_spike:
            confidence = min(confidence + 0.15, 1.0)

        signal = {
            "slug": slug,
            "title": title,
            "signal_type": signal_type,
            "price_before": prev_price,
            "price_after": new_price,
            "move_cents": move_cents,
            "move_direction": move_direction,
            "news_count_4h": len(related_news),
            "news_consensus": consensus,
            "confidence": confidence,
            "category": new.get("category"),
            "volume_spike": volume_spike,
        }

        reasoning_en, reasoning_vn = build_reasoning(signal)
        signal["reasoning_en"] = reasoning_en
        signal["reasoning_vn"] = reasoning_vn

        del signal["volume_spike"]

        signals.append(signal)

    return signals
