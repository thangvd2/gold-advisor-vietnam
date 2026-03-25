"""Tests for Telegram bot command handlers (Plan 06-01)."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.engine.types import Recommendation, Signal, SignalMode


@pytest.fixture
def mock_application():
    app = MagicMock()
    app.initialize = AsyncMock()
    app.shutdown = AsyncMock()
    app.start = AsyncMock()
    app.stop = AsyncMock()
    return app


class TestStartHandler:
    @pytest.mark.asyncio
    async def test_registers_chat_id(self):
        from src.alerts.bot import start_handler

        update = MagicMock()
        update.effective_chat.id = 12345
        context = MagicMock()

        from src.alerts import bot

        bot.SUBSCRIBED_CHATS.discard(12345)

        await start_handler(update, context)

        assert 12345 in bot.SUBSCRIBED_CHATS

    @pytest.mark.asyncio
    async def test_replies_with_welcome_message(self):
        from src.alerts.bot import start_handler

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await start_handler(update, context)

        update.message.reply_text.assert_called_once()
        message = update.message.reply_text.call_args[0][0]
        assert "Gold Advisor" in message
        assert (
            "không phải tư vấn" in message or "not financial advice" in message.lower()
        )

    @pytest.mark.asyncio
    async def test_registers_chat_id(self):
        from src.alerts.bot import start_handler

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        from src.alerts import bot

        bot.SUBSCRIBED_CHATS.discard(12345)

        await start_handler(update, context)

        assert 12345 in bot.SUBSCRIBED_CHATS

    @pytest.mark.asyncio
    async def test_replies_with_welcome_message(self):
        from src.alerts.bot import start_handler

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await start_handler(update, context)

        update.message.reply_text.assert_called_once()
        message = update.message.reply_text.call_args[0][0]
        assert "Gold Advisor" in message
        assert (
            "không phải tư vấn" in message or "not financial advice" in message.lower()
        )

    @pytest.mark.asyncio
    async def test_replies_with_disclaimer(self):
        from src.alerts.bot import start_handler

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        await start_handler(update, context)

        message = update.message.reply_text.call_args[0][0]
        assert "tư vấn" in message or "advice" in message.lower()


class TestStatusHandler:
    @pytest.mark.asyncio
    async def test_replies_with_signal_data(self):
        from src.alerts import bot as bot_module
        from src.alerts.bot import status_handler

        bot_module._db_path = "/tmp/test.db"

        signal = Signal(
            recommendation=Recommendation.BUY,
            confidence=75,
            factors=[],
            reasoning="Gap narrowed to 2.8%",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
            gap_vnd=5_000_000,
            gap_pct=2.6,
        )

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("src.alerts.bot.compute_signal", return_value=signal):
            await status_handler(update, context)

        update.message.reply_text.assert_called_once()
        message = update.message.reply_text.call_args[0][0]
        assert "BUY" in message or "MUA" in message
        assert "75" in message

    @pytest.mark.asyncio
    async def test_handles_insufficient_data(self):
        from src.alerts import bot as bot_module
        from src.alerts.bot import status_handler

        bot_module._db_path = "/tmp/test.db"

        signal = Signal(
            recommendation=Recommendation.HOLD,
            confidence=0,
            factors=[],
            reasoning="Insufficient data for signal analysis",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
        )

        update = MagicMock()
        update.effective_chat.id = 12345
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        with patch("src.alerts.bot.compute_signal", return_value=signal):
            await status_handler(update, context)

        message = update.message.reply_text.call_args[0][0]
        assert "Chưa đủ dữ liệu" in message or "Insufficient" in message


class TestFormatSignalMessage:
    def test_buy_signal_has_green_emoji(self):
        from src.alerts.bot import _format_signal_message

        signal = Signal(
            recommendation=Recommendation.BUY,
            confidence=75,
            reasoning="Gap favorable",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
            gap_vnd=5_000_000,
            gap_pct=2.6,
        )

        message = _format_signal_message(signal)
        assert "BUY" in message or "MUA" in message
        assert "75" in message

    def test_hold_signal(self):
        from src.alerts.bot import _format_signal_message

        signal = Signal(
            recommendation=Recommendation.HOLD,
            confidence=50,
            reasoning="Waiting",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
        )

        message = _format_signal_message(signal)
        assert "HOLD" in message or "GIỮ" in message

    def test_sell_signal(self):
        from src.alerts.bot import _format_signal_message

        signal = Signal(
            recommendation=Recommendation.SELL,
            confidence=80,
            reasoning="Gap too high",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
            gap_vnd=15_000_000,
            gap_pct=8.0,
        )

        message = _format_signal_message(signal)
        assert "SELL" in message or "BÁN" in message

    def test_includes_disclaimer(self):
        from src.alerts.bot import _format_signal_message

        signal = Signal(
            recommendation=Recommendation.BUY,
            confidence=75,
            reasoning="Test",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
        )

        message = _format_signal_message(signal)
        assert "tư vấn" in message or "advice" in message.lower()

    def test_includes_gap_info(self):
        from src.alerts.bot import _format_signal_message

        signal = Signal(
            recommendation=Recommendation.BUY,
            confidence=75,
            reasoning="Test",
            mode=SignalMode.SAVER,
            timestamp=datetime.now(timezone.utc),
            gap_vnd=5_000_000,
            gap_pct=2.6,
        )

        message = _format_signal_message(signal)
        assert "5,000,000" in message or "5.0" in message


class TestBotLifecycle:
    @pytest.mark.asyncio
    async def test_start_bot_with_empty_token_no_crash(self):
        from src.alerts.bot import start_bot

        with patch("src.alerts.bot.Settings") as mock_settings:
            mock_settings.return_value.telegram_bot_token = ""
            await start_bot("/tmp/test.db")

    @pytest.mark.asyncio
    async def test_start_bot_with_token_initializes_app(self):
        from src.alerts.bot import start_bot

        with (
            patch("src.alerts.bot.Settings") as mock_settings,
            patch("src.alerts.bot.Application") as mock_app_builder,
        ):
            mock_settings.return_value.telegram_bot_token = "fake-token"
            mock_app = MagicMock()
            mock_app.initialize = AsyncMock()
            mock_app.start = AsyncMock()
            mock_app.updater.start_polling = AsyncMock()
            mock_app_builder.builder.return_value.token.return_value.build.return_value = mock_app

            await start_bot("/tmp/test.db")

            mock_app.initialize.assert_awaited_once()
            mock_app.start.assert_awaited_once()
            mock_app.updater.start_polling.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stop_bot_with_no_bot_no_crash(self):
        from src.alerts.bot import stop_bot

        from src.alerts import bot

        bot._application = None
        await stop_bot()

    @pytest.mark.asyncio
    async def test_start_bot_extracts_db_path_from_uri(self):
        """start_bot strips SQLAlchemy URI prefix to get raw .db path."""
        from src.alerts import bot as bot_module
        from src.alerts.bot import start_bot

        with (
            patch("src.alerts.bot.Settings") as mock_settings,
            patch("src.alerts.bot.Application") as mock_app_builder,
        ):
            mock_settings.return_value.telegram_bot_token = "fake-token"
            mock_app = MagicMock()
            mock_app.initialize = AsyncMock()
            mock_app.start = AsyncMock()
            mock_app.updater.start_polling = AsyncMock()
            mock_app_builder.builder.return_value.token.return_value.build.return_value = mock_app

            await start_bot("sqlite+aiosqlite:///./gold_advisor.db")

            assert bot_module._db_path == "gold_advisor.db"

    @pytest.mark.asyncio
    async def test_start_bot_handles_relative_path_uri(self):
        """start_bot expands relative path from URI."""
        from src.alerts import bot as bot_module
        from src.alerts.bot import start_bot

        with (
            patch("src.alerts.bot.Settings") as mock_settings,
            patch("src.alerts.bot.Application") as mock_app_builder,
        ):
            mock_settings.return_value.telegram_bot_token = "fake-token"
            mock_app = MagicMock()
            mock_app.initialize = AsyncMock()
            mock_app.start = AsyncMock()
            mock_app.updater.start_polling = AsyncMock()
            mock_app_builder.builder.return_value.token.return_value.build.return_value = mock_app

            await start_bot("sqlite+aiosqlite:///data/test.db")

            assert "data/test.db" in bot_module._db_path

    @pytest.mark.asyncio
    async def test_start_bot_handles_tilde_home_path(self):
        """start_bot expands ~ in db path."""
        from src.alerts import bot as bot_module
        from src.alerts.bot import start_bot

        with (
            patch("src.alerts.bot.Settings") as mock_settings,
            patch("src.alerts.bot.Application") as mock_app_builder,
        ):
            mock_settings.return_value.telegram_bot_token = "fake-token"
            mock_app = MagicMock()
            mock_app.initialize = AsyncMock()
            mock_app.start = AsyncMock()
            mock_app.updater.start_polling = AsyncMock()
            mock_app_builder.builder.return_value.token.return_value.build.return_value = mock_app

            await start_bot("sqlite+aiosqlite:///~/gold.db")

            assert bot_module._db_path.startswith("/")
