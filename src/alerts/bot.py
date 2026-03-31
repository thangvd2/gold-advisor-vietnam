import asyncio
import logging
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from src.config import Settings, VNTZ
from src.engine.pipeline import compute_signal
from src.engine.types import Recommendation, Signal, SignalMode

logger = logging.getLogger(__name__)

SUBSCRIBED_CHATS: set[int] = set()
_application: Application | None = None
_db_path: str = ""

LOCAL_STORE_NAME = "Tiệm vàng gần nhà"

_DATE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})$")
_TIME_RE = re.compile(r"^(\d{1,2}:\d{2})$")
_DATETIME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2})$")


def _parse_vn_datetime(args: list[str]) -> datetime | None:
    """Parse optional date/time arguments as Vietnam timezone, return UTC datetime.

    Supported formats from args[2:]:
      - (none) → now
      - YYYY-MM-DD → that date, current time
      - HH:MM → today at that time
      - YYYY-MM-DD HH:MM → exact date and time

    Returns a UTC-aware datetime, or None if parsing fails.
    """
    if len(args) < 3:
        return None

    remainder = " ".join(args[2:]).strip()

    m = _DATETIME_RE.match(remainder)
    if m:
        dt_str = f"{m.group(1)} {m.group(2)}"
        try:
            return (
                datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
                .replace(tzinfo=VNTZ)
                .astimezone(timezone.utc)
            )
        except ValueError:
            return None

    m = _DATE_RE.match(remainder)
    if m:
        try:
            return (
                datetime.strptime(m.group(1), "%Y-%m-%d")
                .replace(
                    hour=datetime.now(VNTZ).hour,
                    minute=datetime.now(VNTZ).minute,
                    tzinfo=VNTZ,
                )
                .astimezone(timezone.utc)
            )
        except ValueError:
            return None

    m = _TIME_RE.match(remainder)
    if m:
        try:
            today = datetime.now(VNTZ).date()
            dt = datetime.strptime(f"{today} {m.group(1)}", "%Y-%m-%d %H:%M")
            return dt.replace(tzinfo=VNTZ).astimezone(timezone.utc)
        except ValueError:
            return None

    return None


def _recommendation_emoji(rec: Recommendation) -> str:
    return {
        Recommendation.BUY: "🟢",
        Recommendation.HOLD: "🟡",
        Recommendation.SELL: "🔴",
    }.get(rec, "⚪")


def _format_signal_message(signal: Signal) -> str:
    emoji = _recommendation_emoji(signal.recommendation)
    lines = [
        f"{emoji} {signal.recommendation.value} (Signal strength: {signal.confidence}%)",
        "",
        f"💡 {signal.reasoning}",
    ]

    if signal.gap_vnd is not None and signal.gap_pct is not None:
        gap_vnd_str = f"{signal.gap_vnd:,.0f}"
        lines.append("")
        lines.append(f"📊 Gap: {gap_vnd_str} VND ({signal.gap_pct:.1f}%)")

    lines.append("")
    lines.append("⚠️ Đây là thông tin thị trường, không phải tư vấn đầu tư.")
    lines.append("Market information only, not financial advice.")
    return "\n".join(lines)


def _save_local_price(
    buy_price: float, sell_price: float, timestamp: datetime | None = None
) -> bool:
    now = timestamp or datetime.now(timezone.utc)
    fetched_at = datetime.now(timezone.utc).isoformat()
    spread = sell_price - buy_price

    conn = sqlite3.connect(_db_path)
    try:
        conn.execute(
            """INSERT INTO price_history
               (source, product_type, buy_price, sell_price, spread,
                price_vnd, currency, timestamp, fetched_at, validation_status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                "local",
                "ring_gold",
                buy_price,
                sell_price,
                spread,
                buy_price,
                "VND",
                now,
                fetched_at,
                "manual",
            ),
        )
        conn.commit()
        return True
    except Exception as e:
        logger.exception("Failed to save local price")
        return False
    finally:
        conn.close()


def _get_local_price() -> dict | None:
    conn = sqlite3.connect(_db_path)
    try:
        row = conn.execute(
            """SELECT buy_price, sell_price, spread, timestamp, fetched_at
               FROM price_history
               WHERE source = 'local' AND product_type = 'ring_gold'
               ORDER BY timestamp DESC LIMIT 1"""
        ).fetchone()
        if row:
            return {
                "buy_price": row[0],
                "sell_price": row[1],
                "spread": row[2],
                "timestamp": row[3],
                "fetched_at": row[4],
            }
        return None
    finally:
        conn.close()


def _get_dealer_ring_prices() -> list[dict]:
    conn = sqlite3.connect(_db_path)
    try:
        rows = conn.execute(
            """SELECT source, buy_price, sell_price, timestamp
               FROM price_history
               WHERE product_type = 'ring_gold'
                 AND source IN ('sjc', 'pnj', 'doji', 'phuquy')
                 AND timestamp >= datetime('now', '-3 hours')
               GROUP BY source
               HAVING MAX(timestamp)
               ORDER BY source"""
        ).fetchall()
        return [
            {"source": r[0], "buy_price": r[1], "sell_price": r[2], "timestamp": r[3]}
            for r in rows
        ]
    finally:
        conn.close()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    SUBSCRIBED_CHATS.add(chat_id)
    logger.info("User %s subscribed to alerts", chat_id)

    welcome = (
        "🪙 Gold Advisor Vietnam Bot\n\n"
        "/status — Xem tín hiệu hiện tại\n"
        "/chat <câu hỏi> — Hỏi AI tư vấn vàng\n"
        "/update <mua> <bán> [ngày] [giờ] — Cập nhật giá nhẫn tiệm gần nhà\n"
        "/price — Xem giá nhẫn tiệm gần nhà vs các đại lý\n"
        "/history — Lịch sử giá nhẫn tiệm gần nhà\n\n"
        "Hoặc nhắn tin trực tiếp để hỏi AI!\n\n"
        "⚠️ Đây là thông tin thị trường, không phải tư vấn đầu tư."
    )
    await update.message.reply_text(welcome)


async def status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _db_path:
        await update.message.reply_text("⚠️ Bot not initialized yet.")
        return

    signal = await asyncio.to_thread(compute_signal, _db_path, SignalMode.SAVER)

    if signal.confidence == 0 and signal.recommendation == Recommendation.HOLD:
        await update.message.reply_text(
            "📊 Chưa đủ dữ liệu để phân tích tín hiệu.\n"
            "Insufficient data for signal analysis."
        )
        return

    message = _format_signal_message(signal)
    await update.message.reply_text(message)


async def update_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _db_path:
        await update.message.reply_text("⚠️ Bot not initialized yet.")
        return

    if not context.args or len(context.args) < 2:
        await update.message.reply_text(
            "ℹ️ Dùng: /update <giá_mua> <giá_bán> [ngày] [giờ]\n"
            "Ví dụ:\n"
            "  /update 175000 176500\n"
            "  /update 175000 176500 11:00\n"
            "  /update 175000 176500 2026-03-24\n"
            "  /update 175000 176500 2026-03-24 11:00\n\n"
            "Giá tính theo nghìn VND/lượng (vd: 175000 = 175.000đ)\n"
            "Thời gian theo giờ Việt Nam (UTC+7)"
        )
        return

    raw_buy = context.args[0].replace(",", "").replace(".", "")
    raw_sell = context.args[1].replace(",", "").replace(".", "")

    try:
        buy_price = float(raw_buy)
        sell_price = float(raw_sell)
    except ValueError:
        await update.message.reply_text(
            "❌ Giá không hợp lệ. Dùng số nguyên, ví dụ: /update 175000 176500"
        )
        return

    if buy_price <= 0 or sell_price <= 0:
        await update.message.reply_text("❌ Giá phải lớn hơn 0.")
        return

    if sell_price <= buy_price:
        await update.message.reply_text("❌ Giá bán phải cao hơn giá mua.")
        return

    if buy_price < 100000 or sell_price > 500000000:
        await update.message.reply_text(
            "❌ Giá không hợp lệ (ngoặc phạm vi thông thường)."
        )
        return

    parsed_ts = _parse_vn_datetime(context.args)

    if len(context.args) >= 3 and parsed_ts is None:
        await update.message.reply_text(
            "❌ Thời gian không hợp lệ.\nDùng: YYYY-MM-DD, HH:MM, hoặc YYYY-MM-DD HH:MM"
        )
        return

    display_time = (
        parsed_ts.astimezone(VNTZ).strftime("%d/%m/%Y %H:%M")
        if parsed_ts
        else datetime.now(VNTZ).strftime("%d/%m/%Y %H:%M")
    )

    success = await asyncio.to_thread(
        _save_local_price, buy_price, sell_price, parsed_ts
    )

    if success:
        spread = sell_price - buy_price
        await update.message.reply_text(
            f"✅ Đã cập nhật giá {LOCAL_STORE_NAME}:\n\n"
            f"    Mua:  {buy_price:,.0f} đ/lượng\n"
            f"    Bán:  {sell_price:,.0f} đ/lượng\n"
            f"    Chênh: {spread:,.0f} đ\n"
            f"    Thời gian: {display_time}"
        )
    else:
        await update.message.reply_text("❌ Lỗi khi lưu giá. Thử lại sau.")


async def price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _db_path:
        await update.message.reply_text("⚠️ Bot not initialized yet.")
        return

    local = await asyncio.to_thread(_get_local_price)
    dealers = await asyncio.to_thread(_get_dealer_ring_prices)

    if not local:
        await update.message.reply_text(
            "📊 Chưa có dữ liệu giá tiệm gần nhà.\n"
            "Dùng /update <mua> <bán> để cập nhật."
        )
        return

    spread = local["sell_price"] - local["buy_price"]
    lines = [
        f"🏪 {LOCAL_STORE_NAME}\n",
        f"    Mua:  {local['buy_price']:,.0f} đ/lượng",
        f"    Bán:  {local['sell_price']:,.0f} đ/lượng",
        f"    Chênh: {spread:,.0f} đ",
    ]

    if dealers:
        lines.append("\n📊 So sánh với các đại lý (nhẫn trơn):")
        for d in dealers:
            d_spread = (
                d["sell_price"] - d["buy_price"]
                if d["buy_price"] and d["sell_price"]
                else 0
            )
            diff = local["buy_price"] - d["buy_price"] if d["buy_price"] else 0
            diff_str = f"+{diff:,.0f}" if diff > 0 else f"{diff:,.0f}"
            lines.append(
                f"\n    {d['source'].upper()}: "
                f"{d['buy_price']:,.0f} / {d['sell_price']:,.0f}"
                f"  (chênh: {diff_str})"
            )

    lines.append(f"\n⏰ Cập nhật: {str(local['timestamp'])[:16]}")
    await update.message.reply_text("\n".join(lines))


async def history_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not _db_path:
        await update.message.reply_text("⚠️ Bot not initialized yet.")
        return

    limit = 10
    conn = sqlite3.connect(_db_path)
    try:
        rows = conn.execute(
            """SELECT buy_price, sell_price, spread, timestamp, MAX(fetched_at) as last_scraped
               FROM price_history
               WHERE source = 'local' AND product_type = 'ring_gold'
               GROUP BY buy_price, sell_price, timestamp
               ORDER BY timestamp DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        await update.message.reply_text("📊 Chưa có dữ liệu. Dùng /update để cập nhật.")
        return

    lines = [f"📜 Lịch sử {LOCAL_STORE_NAME} ({len(rows)} lần thay đổi giá):\n"]
    for r in rows:
        ts = (
            datetime.fromisoformat(str(r[3]))
            .replace(tzinfo=timezone.utc)
            .astimezone(VNTZ)
            .strftime("%d/%m/%Y %H:%M")
        )
        scraped = (
            datetime.fromisoformat(str(r[4]))
            .replace(tzinfo=timezone.utc)
            .astimezone(VNTZ)
            .strftime("%d/%m %H:%M")
        )
        lines.append(
            f"  {ts}  M: {r[0]:,.0f}  B: {r[1]:,.0f}  ({r[2]:,.0f})  [cập nhật: {scraped}]"
        )

    await update.message.reply_text("\n".join(lines))


async def chat_command_handler(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    if not context.args:
        await update.message.reply_text(
            "ℹ️ Dùng: /chat <câu hỏi>\nVí dụ: /chat Có nên mua vàng lúc này không?"
        )
        return

    question = " ".join(context.args)
    await _handle_ai_question(update, question)


async def smart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show recent smart money signals from Polymarket."""
    chat_id = update.effective_chat.id
    SUBSCRIBED_CHATS.add(chat_id)
    await update.message.chat.send_action("typing")

    from src.storage.database import async_session
    from src.storage.repository import get_recent_smart_signals

    try:
        async with async_session() as session:
            signals = await get_recent_smart_signals(
                session, hours=48, limit=5, min_confidence=0.5
            )

        if not signals:
            await update.message.reply_text(
                "🔮 No smart money signals in the last 48 hours.\n"
                "Không có tín hiệu smart money trong 48 giờ qua."
            )
            return

        for sig in signals:
            text = _format_smart_signal_card(sig)
            await update.message.reply_text(text=text)
    except Exception:
        logger.exception("Smart money query failed")
        await update.message.reply_text(
            "❌ Lỗi khi truy vấn tín hiệu smart money.\n"
            "Error fetching smart money signals."
        )


def _format_smart_signal_card(sig) -> str:
    """Format a PolymarketSmartSignal ORM object as a Telegram message card."""
    arrow = "📈" if sig.move_direction == "up" else "📉"
    confidence_pct = int(sig.confidence * 100)

    lines = [
        "🔮 Smart Money Signal",
        "",
        f"📌 {sig.title}",
        f"Category: {sig.category or 'N/A'} | Type: {sig.signal_type}",
        f"{arrow} {sig.move_cents}% move (confidence: {confidence_pct}%)",
        "",
        f"📊 Market Consensus: {sig.news_consensus}",
        f"{sig.news_count_4h} related news articles in last 4 hours",
        "",
        f"💡 {sig.reasoning_vn}",
        "",
        f"💡 {sig.reasoning_en}",
        "",
        "⚠️ Thông tin thị trường, không phải tư vấn đầu tư.",
        "Market information only, not financial advice.",
    ]
    return "\n".join(lines)


async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    if update.message.text.startswith("/"):
        return

    await _handle_ai_question(update, update.message.text)


async def _handle_ai_question(update: Update, question: str) -> None:
    await update.message.chat.send_action("typing")

    try:
        from src.advisor.agent import ask_advisor

        result = await ask_advisor(question)
        response_text = result.get("text", "Không có phản hồi.")

        if len(response_text) > 4000:
            for i in range(0, len(response_text), 4000):
                await update.message.reply_text(response_text[i : i + 4000])
        else:
            await update.message.reply_text(response_text)
    except ValueError as e:
        await update.message.reply_text(f"⚠️ {e}")
    except Exception as e:
        logger.exception("AI chat error")
        await update.message.reply_text(
            "❌ Xảy ra lỗi khi xử lý câu hỏi. Vui lòng thử lại sau."
        )


async def start_bot(db_path: str) -> None:
    global _application, _db_path

    # Extract raw .db path from SQLAlchemy URI like "sqlite+aiosqlite:///./gold_advisor.db"
    db_path_clean = db_path
    if ":///" in db_path:
        db_path_clean = db_path.split(":///", 1)[1]
    _db_path = str(Path(db_path_clean).expanduser())
    settings = Settings()
    token = settings.telegram_bot_token

    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return

    global _application
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("status", status_handler))
    app.add_handler(CommandHandler("update", update_handler))
    app.add_handler(CommandHandler("price", price_handler))
    app.add_handler(CommandHandler("history", history_handler))
    app.add_handler(CommandHandler("chat", chat_command_handler))
    app.add_handler(CommandHandler("smart", smart_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    _application = app
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot polling started")


async def stop_bot() -> None:
    global _application

    if _application is not None:
        try:
            await _application.updater.stop()
            await _application.stop()
            await _application.shutdown()
        except Exception:
            logger.exception("Error stopping Telegram bot")
        _application = None
        logger.info("Telegram bot stopped")
