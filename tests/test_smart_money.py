import json
from datetime import datetime, timezone, timedelta

import pytest

from src.ingestion.polymarket.smart_money import (
    build_reasoning,
    classify_news_consensus,
    detect_smart_moves,
    find_related_news,
    get_move_threshold,
)


class TestGetMoveThreshold:
    def test_thin_market_none(self):
        assert get_move_threshold(None) == 5.0

    def test_thin_market_low(self):
        assert get_move_threshold(10000) == 5.0

    def test_thin_market_boundary(self):
        assert get_move_threshold(49999) == 5.0

    def test_moderate_market(self):
        assert get_move_threshold(100000) == 3.0

    def test_moderate_market_boundary(self):
        assert get_move_threshold(249999) == 3.0

    def test_deep_market(self):
        assert get_move_threshold(500000) == 2.0


class TestFindRelatedNews:
    def test_keyword_match_title(self):
        news = [{"title": "Fed rate cut expected next month", "excerpt": ""}]
        result = find_related_news("Federal Reserve rate decision", news)
        assert len(result) == 1

    def test_keyword_match_excerpt(self):
        news = [
            {
                "title": "Markets rally",
                "excerpt": "The federal reserve announced a rate cut.",
            }
        ]
        result = find_related_news("Fed decision coming", news)
        assert len(result) == 1

    def test_no_match(self):
        news = [{"title": "Sports update: local team wins championship", "excerpt": ""}]
        result = find_related_news("Federal Reserve rate decision", news)
        assert len(result) == 0

    def test_empty_news(self):
        result = find_related_news("Gold price surge", [])
        assert result == []

    def test_multiple_matches(self):
        news = [
            {"title": "Gold price drops sharply today", "excerpt": ""},
            {"title": "Stock market gold rally", "excerpt": "Investors buy gold"},
            {"title": "Sports news", "excerpt": ""},
        ]
        result = find_related_news("Gold price movement", news)
        assert len(result) == 2

    def test_stopwords_filtered(self):
        news = [{"title": "The rate is going up", "excerpt": ""}]
        result = find_related_news("Rate decision", news)
        assert len(result) == 1


class TestClassifyNewsConsensus:
    def test_empty_news(self):
        assert classify_news_consensus([], "up") == "none"

    def test_supports_down(self):
        news = [
            {"title": "Market crash fears grow", "excerpt": "Prices decline rapidly"}
        ]
        assert classify_news_consensus(news, "down") == "supports"

    def test_supports_up(self):
        news = [
            {"title": "Economic growth exceeds expectations", "excerpt": "Strong rally"}
        ]
        assert classify_news_consensus(news, "up") == "supports"

    def test_contradicts_down(self):
        news = [
            {
                "title": "Economic recovery stronger than expected",
                "excerpt": "Growth surge",
            }
        ]
        assert classify_news_consensus(news, "down") == "contradicts"

    def test_contradicts_up(self):
        news = [
            {"title": "Recession fears intensify", "excerpt": "Risk of crash increases"}
        ]
        assert classify_news_consensus(news, "up") == "contradicts"

    def test_tied_returns_none(self):
        news = [{"title": "Mixed signals on growth and decline", "excerpt": ""}]
        result = classify_news_consensus(news, "up")
        assert result == "none"

    def test_multiple_articles_consensus(self):
        news = [
            {
                "title": "Markets plunge on recession fears",
                "excerpt": "Decline accelerates",
            },
            {"title": "Economic slowdown deepens", "excerpt": "Weak growth forecast"},
        ]
        assert classify_news_consensus(news, "down") == "supports"


class TestDetectSmartMoves:
    def _make_snap(
        self, slug, price, volume=None, liquidity=None, fetched_at=None, title=None
    ):
        return {
            "slug": slug,
            "title": title or f"Test event {slug}",
            "yes_price": price,
            "volume_24h": volume,
            "liquidity": liquidity,
            "one_day_change": None,
            "category": "Test",
            "fetched_at": fetched_at or datetime.now(timezone.utc),
        }

    def test_no_previous_snapshot(self):
        new = [self._make_snap("test-1", 0.60)]
        signals = detect_smart_moves(new, [], [])
        assert signals == []

    def test_move_below_threshold(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.60, liquidity=100000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [self._make_snap("test-1", 0.605, liquidity=100000, title="Small move")]
        signals = detect_smart_moves(new, prev, [])
        assert signals == []

    def test_contrarian_signal(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.55, liquidity=100000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [
            self._make_snap(
                "test-1", 0.65, liquidity=100000, title="Economy recession outlook"
            )
        ]
        news = [
            {
                "title": "Recession fears grow as economy slows",
                "excerpt": "Market decline expected",
            }
        ]
        signals = detect_smart_moves(new, prev, news)
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "contrarian"
        assert signals[0]["move_direction"] == "up"
        assert signals[0]["news_consensus"] == "contradicts"
        assert signals[0]["confidence"] == 0.8

    def test_no_news_signal(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.50, liquidity=100000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [
            self._make_snap(
                "test-1", 0.65, liquidity=100000, title="Niche political event"
            )
        ]
        signals = detect_smart_moves(new, prev, [])
        assert len(signals) == 1
        assert signals[0]["signal_type"] == "no_news"
        assert signals[0]["confidence"] == 0.5

    def test_no_news_below_2x_threshold(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.55, liquidity=100000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [self._make_snap("test-1", 0.581, liquidity=100000, title="Niche event")]
        move_cents = abs(0.581 - 0.55) * 100
        assert 3.0 < move_cents < 6.0
        signals = detect_smart_moves(new, prev, [])
        assert signals == []

    def test_news_supports_move_filtered(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.55, liquidity=100000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [
            self._make_snap(
                "test-1", 0.65, liquidity=100000, title="Economic growth forecast"
            )
        ]
        news = [
            {
                "title": "Strong growth rally expected",
                "excerpt": "Markets surge on recovery",
            }
        ]
        signals = detect_smart_moves(new, prev, news)
        assert signals == []

    def test_volume_spike_bonus(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1",
                0.50,
                volume=1000,
                liquidity=100000,
                fetched_at=now - timedelta(hours=1),
            )
        ]
        new = [
            self._make_snap(
                "test-1",
                0.65,
                volume=10000,
                liquidity=100000,
                title="Economy recession",
            )
        ]
        news = [{"title": "Recession fears deepen", "excerpt": "Economic decline"}]
        signals = detect_smart_moves(new, prev, news)
        assert len(signals) == 1
        assert signals[0]["confidence"] == pytest.approx(0.95)

    def test_thin_market_higher_threshold(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.55, liquidity=10000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [self._make_snap("test-1", 0.581, liquidity=10000, title="Niche event")]
        move_cents = abs(0.581 - 0.55) * 100
        assert 3.0 < move_cents < 5.0
        signals = detect_smart_moves(new, prev, [])
        assert signals == []

    def test_deep_market_lower_threshold(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.55, liquidity=500000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [
            self._make_snap(
                "test-1", 0.581, liquidity=500000, title="Growth forecast outlook"
            )
        ]
        news = [
            {
                "title": "Growth outlook dims as recession fears mount",
                "excerpt": "Economic slowdown deepens",
            }
        ]
        signals = detect_smart_moves(new, prev, news)
        assert len(signals) == 1

    def test_confidence_cap_at_1(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1",
                0.40,
                volume=100,
                liquidity=100000,
                fetched_at=now - timedelta(hours=1),
            )
        ]
        new = [
            self._make_snap(
                "test-1",
                0.70,
                volume=10000,
                liquidity=100000,
                title="Economy weakening",
            )
        ]
        news = [
            {
                "title": "Economy weakening despite positive headlines",
                "excerpt": "Recession looming",
            }
        ]
        signals = detect_smart_moves(new, prev, news)
        assert signals[0]["confidence"] <= 1.0

    def test_bilingual_reasoning(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1",
                0.50,
                volume=1000,
                liquidity=100000,
                fetched_at=now - timedelta(hours=1),
            )
        ]
        new = [
            self._make_snap(
                "test-1",
                0.65,
                volume=10000,
                liquidity=100000,
                title="Economy recession",
            )
        ]
        news = [{"title": "Recession fears grow", "excerpt": "Decline expected"}]
        signals = detect_smart_moves(new, prev, news)
        assert len(signals) == 1
        assert "reasoning_en" in signals[0]
        assert "reasoning_vn" in signals[0]
        assert signals[0]["reasoning_en"] != ""
        assert signals[0]["reasoning_vn"] != ""
        assert "tăng" in signals[0]["reasoning_vn"]

    def test_down_move_contrain_signal(self):
        now = datetime.now(timezone.utc)
        prev = [
            self._make_snap(
                "test-1", 0.70, liquidity=100000, fetched_at=now - timedelta(hours=1)
            )
        ]
        new = [
            self._make_snap(
                "test-1", 0.55, liquidity=100000, title="Economic recovery outlook"
            )
        ]
        news = [
            {
                "title": "Strong economic recovery expected",
                "excerpt": "Growth surge positive",
            }
        ]
        signals = detect_smart_moves(new, prev, news)
        assert len(signals) == 1
        assert signals[0]["move_direction"] == "down"
        assert signals[0]["signal_type"] == "contrarian"


class TestBuildReasoning:
    def test_contrarian_up(self):
        signal = {
            "move_direction": "up",
            "move_cents": 8.3,
            "news_count_4h": 3,
            "signal_type": "contrarian",
            "volume_spike": False,
        }
        en, vn = build_reasoning(signal)
        assert "up" in en
        assert "8.3" in en
        assert "3" in en
        assert "tăng" in vn

    def test_contrarian_down(self):
        signal = {
            "move_direction": "down",
            "move_cents": 5.1,
            "news_count_4h": 1,
            "signal_type": "contrarian",
            "volume_spike": False,
        }
        en, vn = build_reasoning(signal)
        assert "down" in en
        assert "giảm" in vn

    def test_no_news(self):
        signal = {
            "move_direction": "up",
            "move_cents": 6.0,
            "news_count_4h": 0,
            "signal_type": "no_news",
            "volume_spike": False,
        }
        en, vn = build_reasoning(signal)
        assert "no related news" in en
        assert "không có tin tức" in vn

    def test_volume_spike_note(self):
        signal = {
            "move_direction": "up",
            "move_cents": 10.0,
            "news_count_4h": 2,
            "signal_type": "contrarian",
            "volume_spike": True,
        }
        en, vn = build_reasoning(signal)
        assert "Volume spike" in en
        assert "đột biến" in vn
