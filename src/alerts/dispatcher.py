import logging

from src.engine.types import Recommendation, Signal, SignalMode
from src.alerts.bot import SUBSCRIBED_CHATS, _application

logger = logging.getLogger(__name__)

DISCLAIMER = "⚠️ Đây là thông tin thị trường, không phải tư vấn đầu tư.\nMarket information only, not financial advice."


class AlertDispatcher:
    SIGNAL_CONFIDENCE_THRESHOLD = 20
    PRICE_CHANGE_THRESHOLD = 0.02

    def __init__(self):
        self._last_signals: dict[SignalMode, Signal] = {}
        self._last_sjc_price: float | None = None

    def _should_alert_confidence(self, old_conf: int, new_conf: int) -> bool:
        return abs(new_conf - old_conf) >= self.SIGNAL_CONFIDENCE_THRESHOLD

    def _format_change_alert(self, old: Signal, new: Signal) -> str:
        lines = [
            "🔄 Signal Changed!",
            f"{old.recommendation.value} → {new.recommendation.value}",
            f"Signal strength: {new.confidence}%",
            "",
            f"💡 {new.reasoning}",
        ]

        if new.gap_vnd is not None and new.gap_pct is not None:
            lines.append(f"📊 Gap: {new.gap_vnd:,.0f} VND ({new.gap_pct:.1f}%)")

        lines.extend(["", DISCLAIMER])
        return "\n".join(lines)

    def _format_confidence_alert(self, old: Signal, new: Signal) -> str:
        direction = "↑" if new.confidence > old.confidence else "↓"
        lines = [
            f"📊 Signal Strength {direction}",
            f"{old.recommendation.value} — {old.confidence}% → {new.confidence}%",
            "",
            f"💡 {new.reasoning}",
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines)

    def _format_price_alert(self, old_price: float, new_price: float) -> str:
        pct_change = (new_price - old_price) / old_price * 100
        direction = "📈" if new_price > old_price else "📉"
        lines = [
            f"{direction} Significant Price Movement",
            f"SJC Bar: {old_price:,.0f} → {new_price:,.0f} VND",
            f"Change: {pct_change:+.1f}%",
            "",
            DISCLAIMER,
        ]
        return "\n".join(lines)

    async def check_signal(self, signal: Signal) -> bool:
        previous = self._last_signals.get(signal.mode)

        if previous is None:
            self._last_signals[signal.mode] = signal
            return False

        alerted = False

        if signal.recommendation != previous.recommendation:
            message = self._format_change_alert(previous, signal)
            await self._send_to_all(message)
            alerted = True
        elif self._should_alert_confidence(previous.confidence, signal.confidence):
            message = self._format_confidence_alert(previous, signal)
            await self._send_to_all(message)
            alerted = True

        self._last_signals[signal.mode] = signal
        return alerted

    async def check_price_movement(self, sjc_price: float) -> bool:
        if self._last_sjc_price is None:
            self._last_sjc_price = sjc_price
            return False

        old_price = self._last_sjc_price
        change_ratio = abs(sjc_price - old_price) / old_price

        if change_ratio >= self.PRICE_CHANGE_THRESHOLD:
            message = self._format_price_alert(old_price, sjc_price)
            await self._send_to_all(message)
            self._last_sjc_price = sjc_price
            return True

        self._last_sjc_price = sjc_price
        return False

    async def _send_to_all(self, message: str) -> None:
        if not SUBSCRIBED_CHATS:
            logger.info("No subscribers — skipping alert")
            return

        if _application is None:
            logger.warning("Bot not running — skipping alert")
            return

        for chat_id in list(SUBSCRIBED_CHATS):
            try:
                await _application.bot.send_message(chat_id=chat_id, text=message)
            except Exception:
                logger.exception("Failed to send alert to %s", chat_id)
