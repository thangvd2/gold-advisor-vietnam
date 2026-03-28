"""Tests for FedWatchFetcher, PolymarketFetcher, and Polymarket monitor."""

from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from src.ingestion.fetchers.fedwatch import FedWatchFetcher
from src.ingestion.fetchers.polymarket import (
    EXCLUDED_CATEGORIES,
    GOLD_MACRO_KEYWORDS,
    GOLD_MACRO_TAGS,
    PolymarketFetcher,
)
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


def _make_event(
    slug="event-a",
    title=None,
    volume="150000",
    day_change=None,
    hour_change=None,
    tag_label=None,
    question=None,
):
    """Helper to build a minimal Polymarket event dict.

    day_change/hour_change are RAW decimal values (0.05 means 5%).
    The fetcher multiplies by 100 internally.
    """
    markets = [{"volume24hr": volume, "volumeNum": volume}]
    if day_change is not None:
        markets[0]["oneDayPriceChange"] = day_change
    if hour_change is not None:
        markets[0]["oneHourPriceChange"] = hour_change
    tags = []
    if tag_label:
        tags = [{"label": tag_label}]
    return {
        "slug": slug,
        "title": title or f"Event {slug}",
        "question": question,
        "tags": tags,
        "markets": markets,
    }


class TestPolymarketFetcher:
    # ── _deduplicate_by_slug ─────────────────────────────────────────────

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

    # ── _get_tag_label ──────────────────────────────────────────────────

    def test_get_tag_label_dict_tag_with_label(self):
        """Extracts label from dict-style tag."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"tags": [{"label": "Economy"}]}
        assert fetcher._get_tag_label(event) == "Economy"

    def test_get_tag_label_string_tag(self):
        """Returns stripped string when tag is a plain string."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"tags": ["  Finance  "]}
        assert fetcher._get_tag_label(event) == "Finance"

    def test_get_tag_label_no_tags(self):
        """Returns None when tags is empty or missing."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        assert fetcher._get_tag_label({"tags": []}) is None
        assert fetcher._get_tag_label({}) is None
        assert fetcher._get_tag_label({"tags": None}) is None

    def test_get_tag_label_picks_first_valid(self):
        """Returns the label from the first tag that has a valid label."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"tags": [{"label": ""}, {"label": "World"}]}
        assert fetcher._get_tag_label(event) == "World"

    # ── _is_excluded_category ───────────────────────────────────────────

    def test_is_excluded_category_sports(self):
        """Sports is in EXCLUDED_CATEGORIES."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"tags": [{"label": "Sports"}]}
        assert fetcher._is_excluded_category(event) is True

    def test_is_excluded_category_crypto(self):
        """Crypto is in EXCLUDED_CATEGORIES."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"tags": [{"label": "Crypto"}]}
        assert fetcher._is_excluded_category(event) is True

    def test_is_excluded_category_economy_not_excluded(self):
        """Economy is NOT in EXCLUDED_CATEGORIES."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"tags": [{"label": "Economy"}]}
        assert fetcher._is_excluded_category(event) is False

    def test_is_excluded_category_no_tag(self):
        """Returns False when event has no tags."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        assert fetcher._is_excluded_category({"tags": []}) is False
        assert fetcher._is_excluded_category({}) is False

    # ── _matches_gold_macro ─────────────────────────────────────────────

    def test_matches_gold_macro_fed_tag(self):
        """Matches when tag label is in GOLD_MACRO_TAGS."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"title": "Something", "tags": [{"label": "Fed"}]}
        assert fetcher._matches_gold_macro(event) is True

    def test_matches_gold_macro_title_keyword(self):
        """Matches when title contains a GOLD_MACRO_KEYWORD."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"title": "Will gold price reach $3000?", "tags": []}
        assert fetcher._matches_gold_macro(event) is True

    def test_matches_gold_macro_question_keyword(self):
        """Matches when question contains a GOLD_MACRO_KEYWORD."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {
            "title": "Market event",
            "question": "Will the Fed cut interest rates?",
            "tags": [],
        }
        assert fetcher._matches_gold_macro(event) is True

    def test_matches_gold_macro_no_match(self):
        """No tag match and no keyword in title/question → False."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = {"title": "Random celebrity news", "tags": [{"label": "Culture"}]}
        assert fetcher._matches_gold_macro(event) is False

    # ── _filter_by_move ─────────────────────────────────────────────────

    def test_filter_by_move_keeps_high_volume_and_change(self):
        """Keeps event where total volume > min and first market change > min."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            _make_event(
                slug="big-move",
                volume="150000",
                day_change=0.10,  # 10% after *100
            ),
        ]
        result = fetcher._filter_by_move(events, min_volume=50000, min_change=5.0)
        assert len(result) == 1
        assert result[0]["slug"] == "big-move"

    def test_filter_by_move_excludes_low_volume(self):
        """Excludes event where total volume is below min_volume."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            _make_event(
                slug="low-vol",
                volume="10000",
                day_change=0.10,
            ),
        ]
        result = fetcher._filter_by_move(events, min_volume=50000, min_change=5.0)
        assert result == []

    def test_filter_by_move_excludes_low_change(self):
        """Excludes event where first market change is below min_change."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            _make_event(
                slug="low-change",
                volume="150000",
                day_change=0.01,  # 1% after *100
            ),
        ]
        result = fetcher._filter_by_move(events, min_volume=50000, min_change=5.0)
        assert result == []

    def test_filter_by_move_custom_thresholds(self):
        """Respects custom min_volume and min_change parameters."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [
            _make_event(
                slug="custom",
                volume="5000",
                day_change=0.04,  # 4% after *100
            ),
        ]
        result = fetcher._filter_by_move(events, min_volume=1000, min_change=3.0)
        assert len(result) == 1

    def test_filter_by_move_sums_all_markets_volume(self):
        """Total volume is the SUM of all markets, not just first."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(slug="multi-mkt", volume="30000", day_change=0.10)
        event["markets"].append({"volume24hr": "30000", "volumeNum": "30000"})
        result = fetcher._filter_by_move(
            events=[event], min_volume=50000, min_change=5.0
        )
        assert len(result) == 1  # 30000 + 30000 = 60000 > 50000

    def test_filter_by_move_empty_list(self):
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        result = fetcher._filter_by_move([], min_volume=50000, min_change=5.0)
        assert result == []

    def test_filter_by_move_no_markets(self):
        """Events with no markets are filtered out."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [{"slug": "no-markets", "markets": []}]
        result = fetcher._filter_by_move(events, min_volume=50000, min_change=5.0)
        assert result == []

    def test_filter_by_move_none_change(self):
        """Event with None change is treated as 0% change, excluded."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        events = [_make_event(slug="none-change", volume="150000", day_change=None)]
        result = fetcher._filter_by_move(events, min_volume=50000, min_change=5.0)
        assert result == []

    # ── _extract_event_fields ───────────────────────────────────────────

    def test_extract_event_fields_all_fields(self):
        """Extracts all expected fields; changes are multiplied by 100."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(
            slug="test-event",
            volume="150000",
            day_change=0.08,  # raw decimal → 8.0%
            hour_change=0.02,  # raw decimal → 2.0%
            tag_label="Finance",
            question="Will X happen?",
        )
        result = fetcher._extract_event_fields(event)

        assert result["slug"] == "test-event"
        assert result["title"] == "Event test-event"
        assert result["question"] == "Will X happen?"
        assert result["volume_24h"] == 150000.0
        assert result["one_day_price_change"] == 8.0  # 0.08 * 100
        assert result["one_hour_price_change"] == 2.0  # 0.02 * 100
        assert result["category"] == "Finance"

    def test_extract_event_fields_sums_all_markets_volume(self):
        """volume_24h is the SUM of all markets' volume, not just first."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(slug="multi", volume="100000")
        event["markets"].append({"volume24hr": "50000", "volumeNum": "50000"})
        result = fetcher._extract_event_fields(event)

        assert result["volume_24h"] == 150000.0

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

    def test_extract_event_fields_handles_none_changes(self):
        """None day/hour changes stay None (not converted to float)."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(day_change=None, hour_change=None)
        result = fetcher._extract_event_fields(event)

        assert result["one_day_price_change"] is None
        assert result["one_hour_price_change"] is None

    def test_extract_event_fields_uses_get_tag_label(self):
        """Category comes from _get_tag_label (dict tags with label key)."""
        fetcher = PolymarketFetcher.__new__(PolymarketFetcher)
        event = _make_event(tag_label="Geopolitics")
        result = fetcher._extract_event_fields(event)

        assert result["category"] == "Geopolitics"


class TestPolymarketFetcherAsync:
    @pytest.mark.asyncio
    async def test_fetch_active_events_raises_on_httpx_error(self):
        fetcher = PolymarketFetcher()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(side_effect=Exception("Connection refused"))

        with pytest.raises(Exception, match="Connection refused"):
            await fetcher._fetch_active_events()

    @pytest.mark.asyncio
    async def test_fetch_active_events_returns_data(self):
        """_fetch_active_events returns parsed JSON and uses closed=false param."""
        fetcher = PolymarketFetcher()
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"slug": "active-1"}]
        mock_resp.raise_for_status = MagicMock()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(return_value=mock_resp)

        result = await fetcher._fetch_active_events()
        assert result == [{"slug": "active-1"}]

        # Verify closed=false param (not active=True)
        call_args = fetcher.client.get.call_args
        assert call_args[1]["params"]["closed"] == "false"

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

        result = await fetcher._search_events("gold+price")
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

        result = await fetcher._search_events("fed+rate")
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

        result = await fetcher._search_events("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_search_events_handles_httpx_error(self):
        """_search_events returns [] on httpx error."""
        fetcher = PolymarketFetcher()
        fetcher.client = AsyncMock()
        fetcher.client.get = AsyncMock(side_effect=Exception("Timeout"))

        result = await fetcher._search_events("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_returns_dict_with_both_keys(self):
        """fetch() returns {"gold_macro": [...], "market_movers": [...]}."""
        fetcher = PolymarketFetcher()

        gold_event = _make_event(
            slug="gold-macro",
            volume="200000",
            day_change=0.10,
            tag_label="Fed",
        )
        mover_event = _make_event(
            slug="mover",
            volume="200000",
            day_change=0.10,
            tag_label="Economy",
        )

        fetcher._fetch_gold_macro_events = AsyncMock(
            return_value=[fetcher._extract_event_fields(gold_event)]
        )
        fetcher._fetch_market_movers = AsyncMock(
            return_value=[fetcher._extract_event_fields(mover_event)]
        )

        result = await fetcher.fetch()

        assert isinstance(result, dict)
        assert "gold_macro" in result
        assert "market_movers" in result
        assert len(result["gold_macro"]) == 1
        assert result["gold_macro"][0]["slug"] == "gold-macro"
        assert len(result["market_movers"]) == 1
        assert result["market_movers"][0]["slug"] == "mover"

    @pytest.mark.asyncio
    async def test_fetch_returns_empty_dict_on_error(self):
        """fetch() returns {"gold_macro": [], "market_movers": []} on error."""
        fetcher = PolymarketFetcher()
        fetcher._fetch_gold_macro_events = AsyncMock(side_effect=Exception("boom"))
        fetcher._fetch_market_movers = AsyncMock()

        result = await fetcher.fetch()
        assert result == {"gold_macro": [], "market_movers": []}

    @pytest.mark.asyncio
    async def test_fetch_closes_client_in_finally(self):
        """fetch() always closes the HTTP client, even on error."""
        fetcher = PolymarketFetcher()
        fetcher._fetch_gold_macro_events = AsyncMock(side_effect=Exception("boom"))
        fetcher._fetch_market_movers = AsyncMock()
        fetcher.client = AsyncMock()

        await fetcher.fetch()
        fetcher.client.aclose.assert_awaited_once()


# ── Polymarket monitor tests ───────────────────────────────────────────────


class TestFlagSignificantMoves:
    def test_flags_event_above_threshold(self):
        """Flags event where abs(one_day_price_change) > threshold AND volume > min."""
        events = [
            {"one_day_price_change": 10.0, "volume_24h": 200000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is True

    def test_flags_negative_change_above_threshold(self):
        """Flags event with large negative change above threshold."""
        events = [
            {"one_day_price_change": -15.0, "volume_24h": 500000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is True

    def test_does_not_flag_below_threshold(self):
        """Events with small change stay unflagged."""
        events = [
            {"one_day_price_change": 3.0, "volume_24h": 200000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is False

    def test_does_not_flag_low_volume(self):
        """Events below volume_min stay unflagged even with large change."""
        events = [
            {"one_day_price_change": 20.0, "volume_24h": 500.0},
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
            {"one_day_price_change": 3.0, "volume_24h": 50000.0},
        ]
        result = flag_significant_moves(events, threshold=2.0, volume_min=1000)
        assert result[0]["is_flagged"] is True

    def test_empty_list(self):
        result = flag_significant_moves([])
        assert result == []

    def test_mutates_in_place_and_returns(self):
        """Adds is_flagged key to each event dict and returns the list."""
        events = [
            {"one_day_price_change": 6.0, "volume_24h": 150000.0},
        ]
        result = flag_significant_moves(events)
        assert result is events
        assert "is_flagged" in events[0]

    def test_boundary_change_exactly_at_threshold(self):
        """Change exactly equal to threshold is NOT flagged (uses >, not >=)."""
        events = [
            {"one_day_price_change": 5.0, "volume_24h": 1001.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is False

    def test_multiple_events_mixed(self):
        """Correctly flags/unflags a mix of events."""
        events = [
            {"one_day_price_change": 10.0, "volume_24h": 200000.0},
            {"one_day_price_change": 3.0, "volume_24h": 200000.0},
            {"one_day_price_change": 10.0, "volume_24h": 500.0},
            {"one_day_price_change": None, "volume_24h": 200000.0},
        ]
        result = flag_significant_moves(events)
        assert result[0]["is_flagged"] is True
        assert result[1]["is_flagged"] is False
        assert result[2]["is_flagged"] is False
        assert result[3]["is_flagged"] is False
