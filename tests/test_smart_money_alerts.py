"""Tests for Telegram smart money alerts."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.alerts.dispatcher import AlertDispatcher


def _make_signal(
    slug="test-event",
    confidence=0.8,
    title="Test Event",
    move_direction="up",
    move_cents=5.0,
    signal_type="contrarian",
    news_consensus="contradicts",
    news_count_4h=3,
):
    return {
        "slug": slug,
        "confidence": confidence,
        "title": title,
        "move_direction": move_direction,
        "move_cents": move_cents,
        "signal_type": signal_type,
        "category": "Finance",
        "news_consensus": news_consensus,
        "news_count_4h": news_count_4h,
        "reasoning_en": "Market moved against news consensus.",
        "reasoning_vn": "Thị trường biến động ngược với đồng thuận tin tức.",
    }


class TestFormatSmartMoneyAlert:
    def test_up_direction(self):
        dispatcher = AlertDispatcher()
        signal = _make_signal(move_direction="up", move_cents=5.0)
        text = dispatcher._format_smart_money_alert(signal)
        assert "📈" in text
        assert "5.0%" in text
        assert "Test Event" in text

    def test_down_direction(self):
        dispatcher = AlertDispatcher()
        signal = _make_signal(move_direction="down", move_cents=8.0)
        text = dispatcher._format_smart_money_alert(signal)
        assert "📉" in text
        assert "8.0%" in text

    def test_contains_bilingual_reasoning(self):
        dispatcher = AlertDispatcher()
        signal = _make_signal()
        text = dispatcher._format_smart_money_alert(signal)
        assert "Market moved against news" in text
        assert "thị trường" in text.lower()

    def test_contains_disclaimer(self):
        dispatcher = AlertDispatcher()
        signal = _make_signal()
        text = dispatcher._format_smart_money_alert(signal)
        assert "Market information only" in text

    def test_confidence_percentage(self):
        dispatcher = AlertDispatcher()
        signal = _make_signal(confidence=0.85)
        text = dispatcher._format_smart_money_alert(signal)
        assert "85%" in text


class TestDispatchSmartMoneyAlerts:
    @pytest.mark.asyncio
    async def test_sends_above_threshold(self):
        dispatcher = AlertDispatcher()
        dispatcher._send_to_all = AsyncMock()

        signals = [_make_signal(confidence=0.8)]
        count = await dispatcher.dispatch_smart_money_alerts(signals)
        assert count == 1
        dispatcher._send_to_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_below_threshold(self):
        dispatcher = AlertDispatcher()
        dispatcher._send_to_all = AsyncMock()
        dispatcher._alerted_slugs_with_timestamp = {}

        signals = [_make_signal(confidence=0.3)]
        count = await dispatcher.dispatch_smart_money_alerts(signals)
        assert count == 0
        dispatcher._send_to_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_dedup_same_slug_within_window(self):
        dispatcher = AlertDispatcher()
        dispatcher._send_to_all = AsyncMock()

        signals = [_make_signal(slug="event-1")]
        count1 = await dispatcher.dispatch_smart_money_alerts(signals)
        count2 = await dispatcher.dispatch_smart_money_alerts(signals)
        assert count1 == 1
        assert count2 == 0
        dispatcher._send_to_all.assert_called_once()

    @pytest.mark.asyncio
    async def test_sends_again_after_ttl_expiry(self):
        dispatcher = AlertDispatcher()
        dispatcher._send_to_all = AsyncMock()

        signals = [_make_signal(slug="event-ttl")]

        await dispatcher.dispatch_smart_money_alerts(signals)

        expired_time = datetime.now(timezone.utc) - timedelta(hours=3)
        dispatcher._alerted_slugs_with_timestamp["event-ttl"] = expired_time

        count = await dispatcher.dispatch_smart_money_alerts(signals)
        assert count == 1
        assert dispatcher._send_to_all.call_count == 2

    @pytest.mark.asyncio
    async def test_empty_signals_list(self):
        dispatcher = AlertDispatcher()
        dispatcher._send_to_all = AsyncMock()

        count = await dispatcher.dispatch_smart_money_alerts([])
        assert count == 0
        dispatcher._send_to_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_subscribers(self):
        dispatcher = AlertDispatcher()
        with patch("src.alerts.dispatcher.SUBSCRIBED_CHATS", set()):
            signals = [_make_signal()]
            count = await dispatcher.dispatch_smart_money_alerts(signals)
            assert count == 1


class TestFormatSmartSignalCard:
    def test_orm_object_format(self):
        from src.alerts.bot import _format_smart_signal_card

        sig = MagicMock()
        sig.title = "Fed Decision"
        sig.category = "Finance"
        sig.signal_type = "contrarian"
        sig.move_direction = "up"
        sig.move_cents = 7.0
        sig.confidence = 0.8
        sig.news_consensus = "contradicts"
        sig.news_count_4h = 2
        sig.reasoning_vn = "Tín hiệu ngược với tin tức."
        sig.reasoning_en = "Signal contradicts news."

        text = _format_smart_signal_card(sig)
        assert "Fed Decision" in text
        assert "📈" in text
        assert "7.0%" in text
        assert "80%" in text
        assert "Tín hiệu ngược" in text

    def test_down_direction_orm(self):
        from src.alerts.bot import _format_smart_signal_card

        sig = MagicMock()
        sig.title = "Gold Price"
        sig.category = "Economics"
        sig.signal_type = "no_news"
        sig.move_direction = "down"
        sig.move_cents = 4.0
        sig.confidence = 0.5
        sig.news_consensus = "none"
        sig.news_count_4h = 0
        sig.reasoning_vn = "Không có tin tức liên quan."
        sig.reasoning_en = "No related news."

        text = _format_smart_signal_card(sig)
        assert "📉" in text
        assert "4.0%" in text
