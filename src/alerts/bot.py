import asyncio
import logging
import threading

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from src.config import Settings
from src.engine.pipeline import compute_signal
from src.engine.types import Recommendation, Signal, SignalMode

logger = logging.getLogger(__name__)

SUBSCRIBED_CHATS: set[int] = set()
_application: Application | None = None
_thread: threading.Thread | None = None
_db_path: str = ""


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


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    SUBSCRIBED_CHATS.add(chat_id)
    logger.info("User %s subscribed to alerts", chat_id)

    welcome = (
        "🪙 Gold Advisor Vietnam Bot\n\n"
        "Use /status to check current signal.\n"
        "/status — Xem tín hiệu hiện tại\n\n"
        "⚠️ Đây là thông tin thị trường, không phải tư vấn đầu tư.\n"
        "Market information only, not financial advice."
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


def start_bot(db_path: str) -> None:
    global _application, _thread, _db_path

    _db_path = db_path
    settings = Settings()
    token = settings.telegram_bot_token

    if not token:
        logger.warning("TELEGRAM_BOT_TOKEN not set — bot disabled")
        return

    def _run_polling():
        global _application
        app = Application.builder().token(token).build()
        app.add_handler(CommandHandler("start", start_handler))
        app.add_handler(CommandHandler("status", status_handler))

        _application = app
        logger.info("Telegram bot starting...")
        app.run_polling()

    _thread = threading.Thread(target=_run_polling, daemon=True)
    _thread.start()


def stop_bot() -> None:
    global _application, _thread

    if _application is not None:
        try:
            _application.stop()
        except Exception:
            logger.exception("Error stopping Telegram bot")
        _application = None

    if _thread is not None and _thread.is_alive():
        _thread.join(timeout=5)
        _thread = None
