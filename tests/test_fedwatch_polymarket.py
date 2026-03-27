"""Tests for FedWatchFetcher, PolymarketFetcher, and Polymarket monitor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.ingestion.fetchers.fedwatch import FedWatchFetcher
from src.ingestion.fetchers.polymarket import PolymarketFetcher
from src.ingestion.polymarket.monitor import flag_significant_moves


# ── FedWatchFetcher tests ──────────────────────────────────────────────────


class TestFedWatchFetcher:
    def test_get_zq_price_returns_implied_rate(self):
        """implied_rate = 100 - close_price (e.g. 96.345 -> 3.655)."""
        mock_df = pd.DataFrame({"Close": [96.0, 96.1, 96.2, 96.345, 96.4]})
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_df

        with patch("src.ingestion.fetchers.fedwatch.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            fetcher = FedWatchFetcher()
            result = fetcher._get_zq_price()

        assert result is not None
        assert result["implied_rate"] == pytest.approx(3.6, abs=1e-9)
        assert result["futures_price"] == pytest.approx(96.4)
        assert result["contract"] == "ZQ=F"

    def test_get_zq_price_implied_rate_calculation(self):
        """Verify implied_rate = 100 - last_close exactly."""
        mock_df = pd.DataFrame({"Close": [95.5, 95.8, 96.0]})
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = mock_df

        with patch("src.ingestion.fetchers.fedwatch.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            fetcher = FedWatchFetcher()
            result = fetcher._get_zq_price()

        assert result["implied_rate"] == pytest.approx(4.0)
        assert result["futures_price"] == pytest.approx(96.0)

    def test_get_zq_price_returns_none_on_empty_df(self):
        """Returns None when yfinance returns empty DataFrame."""
        mock_ticker = MagicMock()
        mock_ticker.history.return_value = pd.DataFrame()

        with patch("src.ingestion.fetchers.fedwatch.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            fetcher = FedWatchFetcher()
            result = fetcher._get_zq_price()

        assert result is None

    def test_get_zq_price_raises_on_exception(self):
        """_get_zq_price propagates exceptions (handled by _fetch_fed_funds)."""
        with patch("src.ingestion.fetchers.fedwatch.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("yfinance error")
            fetcher = FedWatchFetcher()
            with pytest.raises(Exception, match="yfinance error"):
                fetcher._get_zq_price()

    @pytest.mark.asyncio
    async def test_fetch_fed_funds_returns_none_on_exception(self):
        """_fetch_fed_funds catches exceptions and returns None."""
        with patch(
            "src.ingestion.fetchers.fedwatch.asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=Exception("yfinance error"),
        ):
            fetcher = FedWatchFetcher()
            result = await fetcher._fetch_fed_funds()

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_returns_dict_with_expected_keys(self):
        """fetch() returns dict with implied_rate, futures_price, contract."""
        expected = {
            "implied_rate": 3.655,
            "futures_price": 96.345,
            "contract": "ZQ=F",
        }

        with patch(
            "src.ingestion.fetchers.fedwatch.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=expected,
        ):
            fetcher = FedWatchFetcher()
            result = await fetcher.fetch()

        assert result is not None
        assert set(result.keys()) == {"implied_rate", "futures_price", "contract"}
        assert result["implied_rate"] == 3.655
        assert result["futures_price"] == 96.345
        assert result["contract"] == "ZQ=F"

    @pytest.mark.asyncio
    async def test_fetch_returns_none_when_to_thread_fails(self):
        """fetch() returns None when asyncio.to_thread raises."""
        with patch(
            "src.ingestion.fetchers.fedwatch.asyncio.to_thread",
            new_callable=AsyncMock,
            side_effect=Exception("thread error"),
        ):
            fetcher = FedWatchFetcher()
            result = await fetcher.fetch()

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_returns_none_when_get_zq_returns_none(self):
        """fetch() returns None when _get_zq_price returns None (empty df)."""
        with patch(
            "src.ingestion.fetchers.fedwatch.asyncio.to_thread",
            new_callable=AsyncMock,
            return_value=None,
        ):
            fetcher = FedWatchFetcher()
            result = await fetcher.fetch()

        assert result is None


# ── PolymarketFetcher unit tests ───────────────────────────────────────────


def _make_event(slug="event-a", volume="150000", day_change=None, hour_change=None):
    """Helper to build a minimal Polymarket event dict."""
    return {
        "id": "abc-123",
        "slug": slug,
        "title": f"Event {slug}",
        "question": "Will X happen?",
        "markets": [
            {
                "outcomePrices": "0.6,0.4",
                "volumeNum": volume,
                "volume24hr": volume,
                "liquidityNum": "50000",
                "oneDayPriceChange": day_change,
                "oneHourPriceChange": hour_change,
            }
        ],
        "tags": [{"name": "Finance"}],
        "categories": [],
    }


class TestPolymarketFetcher:
    def test_deduplicate_by_slug_removes_dupes(self):
        """_deduplicate_by_slug keeps only the first occurrence per slug/id."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            {"slug": "a", "id": "1"},
            {"slug": "a", "id": "2"},
            {"slug": "b", "id": "3"},
        ]
        result = fetcher._deduplicate_by_slug(events)
        assert len(result) == 2
        assert result[0]["slug"] == "a"
        assert result[1]["slug"] == "b"

    def test_deduplicate_by_slug_uses_id_when_no_slug(self):
        """Falls back to 'id' field when 'slug' is missing."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            {"id": "x", "title": "first"},
            {"id": "x", "title": "duplicate"},
            {"id": "y", "title": "unique"},
        ]
        result = fetcher._deduplicate_by_slug(events)
        assert len(result) == 2
        assert result[0]["title"] == "first"
        assert result[1]["title"] == "unique"

    def test_deduplicate_by_slug_empty_list(self):
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        result = fetcher._deduplicate_by_slug([])
        assert result == []

    def test_deduplicate_by_slug_skips_missing_slug_and_id(self):
        """Events with no slug or id are dropped (slug would be falsy)."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            {"title": "no identifier"},
            {"slug": "has-slug"},
        ]
        result = fetcher._deduplicate_by_slug(events)
        assert len(result) == 1
        assert result[0]["slug"] == "has-slug"

    def test_filter_by_volume_keeps_high_volume(self):
        """Keeps events where at least one market exceeds min_volume."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            _make_event(volume="150000"),
            _make_event(volume="50000"),
        ]
        result = fetcher._filter_by_volume(events, min_volume=100000)
        assert len(result) == 1
        assert result[0]["slug"] == "event-a"

    def test_filter_by_volume_custom_min_volume(self):
        """Respects custom min_volume threshold."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            _make_event(slug="event-a", volume="50000"),
            _make_event(slug="event-b", volume="200000"),
        ]
        result = fetcher._filter_by_volume(events, min_volume=100000)
        assert len(result) == 1
        assert result[0]["slug"] == "event-b"

    def test_filter_by_volume_empty_list(self):
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        result = fetcher._filter_by_volume([])
        assert result == []

    def test_filter_by_volume_handles_no_markets(self):
        """Events with no markets dict are filtered out."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [{"slug": "no-markets", "markets": []}]
        result = fetcher._filter_by_volume(events)
        assert result == []

    def test_filter_by_volume_handles_invalid_volume_string(self):
        """Non-numeric volume treated as 0, event filtered out."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            {
                "slug": "bad-volume",
                "markets": [{"volumeNum": "not-a-number"}],
            }
        ]
        result = fetcher._filter_by_volume(events)
        assert result == []

    def test_extract_event_fields_all_fields(self):
        """Extracts all expected fields from a complete event dict."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(
            slug="test-event",
            volume="150000",
            day_change=0.08,
            hour_change=0.02,
        )
        result = fetcher._extract_event_fields(event)

        assert result["slug"] == "test-event"
        assert result["title"] == "Event test-event"
        assert result["question"] == "Will X happen?"
        assert result["outcome_prices"] == "0.6,0.4"
        assert result["volume_24h"] == 150000.0
        assert result["liquidity"] == 50000.0
        assert result["one_day_price_change"] == 0.08
        assert result["one_hour_price_change"] == 0.02
        assert result["category"] == "Finance"

    def test_extract_event_fields_no_markets(self):
        """Defaults to 0.0/None when event has no markets."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"slug": "empty", "title": "No markets", "markets": []}
        result = fetcher._extract_event_fields(event)

        assert result["slug"] == "empty"
        assert result["title"] == "No markets"
        assert result["outcome_prices"] is None
        assert result["volume_24h"] == 0.0
        assert result["liquidity"] == 0.0
        assert result["one_day_price_change"] is None
        assert result["one_hour_price_change"] is None
        assert result["category"] is None

    def test_extract_event_fields_uses_categories_as_fallback(self):
        """Falls back to categories[0] when tags is empty."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event()
        event["tags"] = []
        event["categories"] = ["Politics"]
        result = fetcher._extract_event_fields(event)

        assert result["category"] == "Politics"

    def test_extract_event_fields_handles_none_changes(self):
        """None day/hour changes stay None (not converted to float)."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(day_change=None, hour_change=None)
        result = fetcher._extract_event_fields(event)

        assert result["one_day_price_change"] is None
        assert result["one_hour_price_change"] is None

    def test_extract_event_fields_handles_dict_category(self):
        """Category as dict extracts name/slug."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event()
        event["tags"] = [{"slug": "economics", "name": "Economics"}]
        result = fetcher._extract_event_fields(event)

        assert result["category"] == "Economics"


class TestPolymarketFetcherAsync:
    @pytest.mark.asyncio
    async def test_fetch_active_events_handles_httpx_error(self):
        """_fetch_active_events returns [] on httpx error."""
        fetcher = PolymarketFetcher()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(side_effect=Exception("Connection refused"))

        result = await fetcher._fetch_active_events()
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_active_events_returns_data(self):
        """_fetch_active_events returns parsed JSON on success."""
        fetcher = PolymarketFetcher()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"slug": "active-1"}]
        mock_resp.raise_for_status = MagicMock()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher._fetch_active_events()
        assert result == [{"slug": "active-1"}]

    @pytest.mark.asyncio
    async def test_search_events_handles_dict_with_events_key(self):
        """_search_events extracts 'events' list from dict response."""
        fetcher = PolymarketFetcher()
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "events": [{"slug": "search-1"}],
            "other_key": "ignored",
        }
        mock_resp.raise_for_status = MagicMock()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher._search_events()
        assert result == [{"slug": "search-1"}]

    @pytest.mark.asyncio
    async def test_search_events_handles_list_response(self):
        """_search_events returns list directly when response is a list."""
        fetcher = PolymarketFetcher()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"slug": "list-1"}]
        mock_resp.raise_for_status = MagicMock()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher._search_events()
        assert result == [{"slug": "list-1"}]

    @pytest.mark.asyncio
    async def test_search_events_handles_unexpected_format(self):
        """_search_events returns [] when response is neither dict nor list."""
        fetcher = PolymarketFetcher()
        mock_resp = MagicMock()
        mock_resp.json.return_value = "unexpected string"
        mock_resp.raise_for_status = MagicMock()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher._search_events()
        assert result == []

    @pytest.mark.asyncio
    async def test_search_events_handles_httpx_error(self):
        """_search_events returns [] on httpx error."""
        fetcher = PolymarketFetcher()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(side_effect=Exception("Timeout"))

        result = await fetcher._search_events()
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_combines_and_filters_events(self):
        """fetch() merges active + search, dedupes, filters, extracts fields."""
        fetcher = PolymarketFetcher()

        high_vol = _make_event(slug="high-vol", volume="200000", day_change=0.1)
        low_vol = _make_event(slug="low-vol", volume="50000")

        fetcher._fetch_active_events = AsyncMock(return_value=[high_vol, low_vol])
        fetcher._search_events = AsyncMock(return_value=[high_vol])

        result = await fetcher.fetch()

        assert len(result) == 1
        assert result[0]["slug"] == "high-vol"
        assert result[0]["volume_24h"] == 200000.0

    @pytest.mark.asyncio
    async def test_fetch_returns_empty_on_error(self):
        """fetch() returns [] when _fetch_all_events raises."""
        fetcher = PolymarketFetcher()
        fetcher._fetch_active_events = AsyncMock(side_effect=Exception("boom"))
        fetcher._search_events = AsyncMock()

        result = await fetcher.fetch()
        assert result == []


# ── Polymarket monitor tests ───────────────────────────────────────────────


class TestFlagSignificantMoves:
    def test_flags_event_above_threshold(self):
        """Flags event where abs(one_day_price_change) > threshold AND volume > min."""
        events = [
            {"one_day_price_change": 0.10, "volume_24h": 200000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is True

    def test_flags_negative_change_above_threshold(self):
        """Flags event with large negative change above threshold."""
        events = [
            {"one_day_price_change": -0.15, "volume_24h": 500000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is True

    def test_does_not_flag_below_threshold(self):
        """Events with small change stay unflagged."""
        events = [
            {"one_day_price_change": 0.01, "volume_24h": 200000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is False

    def test_does_not_flag_low_volume(self):
        """Events below volume_min stay unflagged even with large change."""
        events = [
            {"one_day_price_change": 0.20, "volume_24h": 50000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is False

    def test_none_change_not_flagged(self):
        """Events with one_day_price_change=None are not flagged."""
        events = [
            {"one_day_price_change": None, "volume_24h": 500000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is False

    def test_custom_threshold_and_volume(self):
        """Respects custom threshold and volume_min parameters."""
        events = [
            {"one_day_price_change": 0.03, "volume_24h": 50000.0},
        ]
        result = flag_significant_moves(events, threshold=0.02, volume_min=10000)
        assert result[0]["is_flagged"] is True

    def test_empty_list(self):
        result = flag_significant_moves([])
        assert result == []

    def test_mutates_in_place_and_returns(self):
        """Adds is_flagged key to each event dict and returns the list."""
        events = [
            {"one_day_price_change": 0.06, "volume_24h": 150000.0},
        ]
        result = flag_significant_moves(events)
        assert result is events
        assert "is_flagged" in events[0]

    def test_boundary_change_exactly_at_threshold(self):
        """Change exactly equal to threshold is NOT flagged (uses >, not >=)."""
        events = [
            {"one_day_price_change": 0.05, "volume_24h": 100001.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is False

    def test_multiple_events_mixed(self):
        """Correctly flags/unflags a mix of events."""
        events = [
            {"one_day_price_change": 0.10, "volume_24h": 200000.0},
            {"one_day_price_change": 0.01, "volume_24h": 200000.0},
            {"one_day_price_change": 0.10, "volume_24h": 50000.0},
            {"one_day_price_change": None, "volume_24h": 200000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is True
        assert result[1]["is_flagged"] is False
        assert result[2]["is_flagged"] is False
        assert result[3]["is_flagged"] is False
