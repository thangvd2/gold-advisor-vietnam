from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone

from agentscope.message._message_block import TextBlock
from agentscope.tool import ToolResponse


def _tool_response(data) -> ToolResponse:
    text = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    return ToolResponse(content=[TextBlock(type="text", text=text)])


def _get_db_path() -> str:
    from src.config import Settings

    settings = Settings()
    url = settings.database_url
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if url.startswith(prefix):
            return url[len(prefix) :]
    return url


def get_current_signal(mode: str = "saver") -> ToolResponse:
    """Get the current BUY/HOLD/SELL signal with confidence and reasoning.

    Args:
        mode: Risk mode - 'saver' for conservative, 'trader' for aggressive. Default 'saver'.
    """
    try:
        from src.engine.pipeline import compute_signal
        from src.engine.types import SignalMode

        db_path = _get_db_path()

        if mode.lower() == "saver":
            selected_mode = SignalMode.SAVER
        else:
            selected_mode = SignalMode.TRADER
        signal = compute_signal(db_path, selected_mode)

        result = {
            "recommendation": signal.recommendation.value,
            "confidence": signal.confidence,
            "reasoning": signal.reasoning,
            "gap_vnd": signal.gap_vnd,
            "gap_pct": signal.gap_pct,
            "factors": [
                {
                    "name": f.name,
                    "direction": f.direction,
                    "weight": f.weight,
                    "confidence": f.confidence,
                }
                for f in signal.factors
            ],
            "mode": signal.mode.value,
            "timestamp": signal.timestamp.isoformat(),
        }
        return _tool_response(result)
    except Exception as e:
        return _tool_response({"error": str(e)})


def get_current_prices() -> ToolResponse:
    """Get the latest gold prices from all dealers (SJC, PNJ, DOJI, Phú Quý)."""
    try:
        db_path = _get_db_path()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT source, product_type, buy_price, sell_price, timestamp
            FROM price_history
            WHERE source IN ('sjc', 'pnj', 'doji', 'phuquy', 'local')
              AND timestamp >= ?
            ORDER BY timestamp DESC
            """,
            (cutoff.isoformat(),),
        )

        rows = cursor.fetchall()
        conn.close()

        latest_by_key: dict[tuple[str, str], dict] = {}
        for row in rows:
            source, product_type, buy_price, sell_price, timestamp = row
            key = (source, product_type)
            if key not in latest_by_key:
                latest_by_key[key] = {
                    "source": source,
                    "product_type": product_type,
                    "buy_price": buy_price,
                    "sell_price": sell_price,
                    "timestamp": timestamp,
                }

        return _tool_response(
            {"prices": list(latest_by_key.values()), "count": len(latest_by_key)}
        )
    except Exception as e:
        return _tool_response({"error": str(e)})


def get_gap_analysis(range: str = "1M") -> ToolResponse:
    """Get the SJC-international gold price gap analysis.

    Args:
        range: Time range for historical gap - '1D', '1W', '1M', '3M', '1Y'. Default '1M'.
    """
    try:
        from src.analysis.gap import calculate_current_gap, calculate_historical_gaps

        db_path = _get_db_path()

        current = calculate_current_gap(db_path)
        if current is None:
            return _tool_response({"error": "No gap data available"})

        historical = calculate_historical_gaps(db_path, range=range)

        gaps = [h["gap_vnd"] for h in historical if h.get("gap_vnd") is not None]
        avg_gap = sum(gaps) / len(gaps) if gaps else None

        trend = "stable"
        if len(gaps) >= 2:
            recent = gaps[-1]
            older = gaps[0]
            diff = recent - older
            threshold = avg_gap * 0.05 if avg_gap else 0
            if diff > threshold:
                trend = "widening"
            elif diff < -threshold:
                trend = "narrowing"

        result = {
            "current_gap_vnd": current.get("gap_vnd"),
            "current_gap_pct": current.get("gap_pct"),
            "avg_sjc_sell": current.get("avg_sjc_sell"),
            "intl_price_vnd": current.get("intl_price_vnd"),
            "historical_avg_gap_vnd": avg_gap,
            "trend": trend,
            "data_points": len(gaps),
            "range": range,
        }
        return _tool_response(result)
    except Exception as e:
        return _tool_response({"error": str(e)})


def get_latest_news(limit: int = 5) -> ToolResponse:
    """Get the latest gold market news items.

    Args:
        limit: Number of news items to return. Default 5, max 20.
    """
    try:
        limit = min(max(1, limit), 20)
        db_path = _get_db_path()

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT title, source, published_at, excerpt, url
            FROM news_items
            ORDER BY published_at DESC
            LIMIT ?
            """,
            (limit,),
        )

        rows = cursor.fetchall()
        conn.close()

        news = [
            {
                "title": row[0],
                "source": row[1],
                "published_at": row[2],
                "excerpt": row[3],
                "url": row[4],
            }
            for row in rows
        ]
        return _tool_response({"news": news, "count": len(news)})
    except Exception as e:
        return _tool_response({"error": str(e)})


def get_macro_indicators() -> ToolResponse:
    """Get current macroeconomic indicators: DXY, USD/VND, gold trend."""
    try:
        db_path = _get_db_path()
        cutoff = datetime.now(timezone.utc) - timedelta(days=7)

        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT product_type, price_usd, price_vnd, timestamp
            FROM price_history
            WHERE product_type IN ('dxy', 'usd_vnd', 'xau_usd')
              AND timestamp >= ?
            ORDER BY timestamp DESC
            """,
            (cutoff.isoformat(),),
        )

        rows = cursor.fetchall()
        conn.close()

        by_type: dict[str, list[tuple]] = {}
        for row in rows:
            product_type, price_usd, price_vnd, timestamp = row
            if product_type not in by_type:
                by_type[product_type] = []
            by_type[product_type].append((price_usd, price_vnd, timestamp))

        def get_trend(values: list[float]) -> str:
            if len(values) < 2:
                return "unknown"
            recent_avg = sum(values[:3]) / min(3, len(values))
            older_avg = sum(values[-3:]) / min(3, len(values))
            diff_pct = (recent_avg - older_avg) / older_avg * 100 if older_avg else 0
            if diff_pct > 0.5:
                return "up"
            elif diff_pct < -0.5:
                return "down"
            return "stable"

        result = {"indicators": {}}

        if "dxy" in by_type and by_type["dxy"]:
            values = [r[0] for r in by_type["dxy"] if r[0]]
            result["indicators"]["dxy"] = {
                "value": values[0] if values else None,
                "trend": get_trend(values),
            }

        if "usd_vnd" in by_type and by_type["usd_vnd"]:
            values = [r[1] for r in by_type["usd_vnd"] if r[1]]
            result["indicators"]["usd_vnd"] = {
                "value": values[0] if values else None,
                "trend": get_trend(values),
            }

        if "xau_usd" in by_type and by_type["xau_usd"]:
            usd_values = [r[0] for r in by_type["xau_usd"] if r[0]]
            vnd_values = [r[1] for r in by_type["xau_usd"] if r[1]]
            result["indicators"]["xau_usd"] = {
                "price_usd": usd_values[0] if usd_values else None,
                "price_vnd": vnd_values[0] if vnd_values else None,
                "trend": get_trend(usd_values),
            }

        return _tool_response(result)
    except Exception as e:
        return _tool_response({"error": str(e)})
