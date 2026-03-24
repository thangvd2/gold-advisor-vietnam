"""Tests for alert dispatcher (Plan 06-02)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine.types import Recommendation, Signal, SignalMode


def _make_signal(
    recommendation=Recommendation.HOLD,
    confidence=50,
    reasoning="No change",
    gap_vnd=None,
    gap_pct=None,
    mode=SignalMode.SAVER,
):
    return Signal(
        recommendation=recommendation,
        confidence=confidence,
        reasoning=reasoning,
        mode=mode,
        timestamp=datetime.now(timezone.utc),
        gap_vnd=gap_vnd,
        gap_pct=gap_pct,
    )


class TestCheckSignal:
    @pytest.mark.asyncio
    async def test_first_signal_no_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        signal = _make_signal(Recommendation.HOLD, 50)

        alerted = await dispatcher.check_signal(signal)

        assert alerted is False

    @pytest.mark.asyncio
    async def test_same_recommendation_no_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        signal1 = _make_signal(Recommendation.HOLD, 50, "First")
        signal2 = _make_signal(Recommendation.HOLD, 55, "Second")

        await dispatcher.check_signal(signal1)
        alerted = await dispatcher.check_signal(signal2)

        assert alerted is False

    @pytest.mark.asyncio
    async def test_recommendation_change_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        signal1 = _make_signal(Recommendation.HOLD, 50)
        signal2 = _make_signal(Recommendation.BUY, 70, "Gap narrowed")

        await dispatcher.check_signal(signal1)

        with patch.object(
            dispatcher, "_send_to_all", new_callable=AsyncMock
        ) as mock_send:
            alerted = await dispatcher.check_signal(signal2)

        assert alerted is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_confidence_crosses_threshold_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        signal1 = _make_signal(Recommendation.HOLD, 50)
        signal2 = _make_signal(Recommendation.HOLD, 75, "Stronger signal")

        await dispatcher.check_signal(signal1)

        with patch.object(
            dispatcher, "_send_to_all", new_callable=AsyncMock
        ) as mock_send:
            alerted = await dispatcher.check_signal(signal2)

        assert alerted is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_confidence_below_threshold_no_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        signal1 = _make_signal(Recommendation.HOLD, 50)
        signal2 = _make_signal(Recommendation.HOLD, 60, "Slight change")

        await dispatcher.check_signal(signal1)

        with patch.object(
            dispatcher, "_send_to_all", new_callable=AsyncMock
        ) as mock_send:
            alerted = await dispatcher.check_signal(signal2)

        assert alerted is False
        mock_send.assert_not_called()


class TestCheckPriceMovement:
    @pytest.mark.asyncio
    async def test_first_price_no_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        alerted = await dispatcher.check_price_movement(195_000_000)

        assert alerted is False

    @pytest.mark.asyncio
    async def test_price_above_threshold_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        await dispatcher.check_price_movement(195_000_000)

        with patch.object(
            dispatcher, "_send_to_all", new_callable=AsyncMock
        ) as mock_send:
            alerted = await dispatcher.check_price_movement(200_000_000)

        assert alerted is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_price_below_threshold_no_alert(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        await dispatcher.check_price_movement(195_000_000)

        with patch.object(
            dispatcher, "_send_to_all", new_callable=AsyncMock
        ) as mock_send:
            alerted = await dispatcher.check_price_movement(196_000_000)

        assert alerted is False
        mock_send.assert_not_called()


class TestFormatAlerts:
    def test_format_change_alert_includes_both_recommendations(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        old = _make_signal(Recommendation.HOLD, 50, "Waiting")
        new = _make_signal(
            Recommendation.BUY, 75, "Gap favorable", gap_vnd=5_000_000, gap_pct=2.6
        )

        message = dispatcher._format_change_alert(old, new)

        assert "HOLD" in message or "GIỮ" in message
        assert "BUY" in message or "MUA" in message
        assert "75" in message

    def test_format_confidence_alert_includes_direction(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        old = _make_signal(Recommendation.HOLD, 50, "Neutral")
        new = _make_signal(Recommendation.HOLD, 75, "Stronger")

        message = dispatcher._format_confidence_alert(old, new)

        assert "75" in message

    def test_format_price_alert_includes_change(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        message = dispatcher._format_price_alert(195_000_000, 200_000_000)

        assert "195" in message or "200" in message

    def test_all_formats_include_disclaimer(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        old = _make_signal(Recommendation.HOLD, 50, "Old")
        new = _make_signal(Recommendation.BUY, 75, "New")

        change_msg = dispatcher._format_change_alert(old, new)
        conf_msg = dispatcher._format_confidence_alert(old, new)
        price_msg = dispatcher._format_price_alert(195_000_000, 200_000_000)

        for msg in [change_msg, conf_msg, price_msg]:
            assert "tư vấn" in msg or "advice" in msg.lower()


class TestSendToAll:
    @pytest.mark.asyncio
    async def test_no_subscribers_skip(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()

        with patch("src.alerts.dispatcher.SUBSCRIBED_CHATS", set()):
            await dispatcher._send_to_all("test message")

    @pytest.mark.asyncio
    async def test_sends_to_each_subscriber(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        mock_bot = MagicMock()
        mock_bot.bot = MagicMock()
        mock_bot.bot.send_message = AsyncMock()

        with (
            patch("src.alerts.dispatcher.SUBSCRIBED_CHATS", {111, 222}),
            patch("src.alerts.dispatcher._application", mock_bot),
        ):
            await dispatcher._send_to_all("test")

        assert mock_bot.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_exception_per_chat_doesnt_crash(self):
        from src.alerts.dispatcher import AlertDispatcher

        dispatcher = AlertDispatcher()
        mock_bot = MagicMock()
        mock_bot.bot = MagicMock()
        mock_bot.bot.send_message = AsyncMock(side_effect=Exception("network error"))

        with (
            patch("src.alerts.dispatcher.SUBSCRIBED_CHATS", {111}),
            patch("src.alerts.dispatcher._application", mock_bot),
        ):
            await dispatcher._send_to_all("test")

        mock_bot.bot.send_message.assert_called_once()
