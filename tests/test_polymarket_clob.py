"""Tests for Polymarket CLOB price history fetcher and backfill."""

import json
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.ingestion.fetchers.polymarket_clob import (
    PricePoint,
    fetch_price_history,
    fetch_price_history_fallback,
)
from src.ingestion.fetchers.polymarket import PolymarketFetcher


class TestPolymarketFetcherTokenIds:
    def test_extract_clob_token_id_from_markets(self):
        fetcher = PolymarketFetcher()
        event = {
            "slug": "test-event",
            "title": "Test",
            "markets": [
                {
                    "clobTokenIds": json.dumps(["0xabc123yes", "0xdef456no"]),
                    "conditionId": "cond-123",
                    "outcomePrices": json.dumps([0.65, 0.35]),
                    "volume24hr": "50000",
                }
            ],
            "tags": [{"label": "Finance"}],
        }
        result = fetcher._extract_event_fields(event)
        assert result["clob_token_id_yes"] == "0xabc123yes"
        assert result["condition_id"] == "cond-123"

    def test_no_markets(self):
        fetcher = PolymarketFetcher()
        event = {"slug": "test", "title": "Test", "markets": []}
        result = fetcher._extract_event_fields(event)
        assert result["clob_token_id_yes"] is None
        assert result["condition_id"] is None

    def test_already_parsed_list(self):
        fetcher = PolymarketFetcher()
        event = {
            "slug": "test",
            "title": "Test",
            "markets": [
                {
                    "clobTokenIds": ["0xalready", "0xparsed"],
                    "conditionId": "cond-456",
                }
            ],
        }
        result = fetcher._extract_event_fields(event)
        assert result["clob_token_id_yes"] == "0xalready"

    def test_invalid_clob_token_ids(self):
        fetcher = PolymarketFetcher()
        event = {
            "slug": "test",
            "title": "Test",
            "markets": [{"clobTokenIds": "not-json"}],
        }
        result = fetcher._extract_event_fields(event)
        assert result["clob_token_id_yes"] is None

    def test_empty_clob_token_ids(self):
        fetcher = PolymarketFetcher()
        event = {
            "slug": "test",
            "title": "Test",
            "markets": [{"clobTokenIds": "[]"}],
        }
        result = fetcher._extract_event_fields(event)
        assert result["clob_token_id_yes"] is None


class TestPricePoint:
    def test_create(self):
        pt = PricePoint(t=1700000000, p=0.65)
        assert pt.t == 1700000000
        assert pt.p == 0.65


class TestFetchPriceHistory:
    @pytest.mark.asyncio
    async def test_returns_price_points(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "history": [{"t": 1700000000, "p": 0.65}, {"t": 1700000060, "p": 0.67}]
        }
        mock_response.headers = {
            "X-RateLimit-Remaining": "900",
            "X-RateLimit-Reset": "0",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        points = await fetch_price_history(
            mock_client, "0xtoken123", 1700000000, 1700000100, fidelity=60
        )

        assert len(points) == 2
        assert points[0].p == 0.65
        assert points[1].p == 0.67

    @pytest.mark.asyncio
    async def test_empty_history(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {"history": []}
        mock_response.headers = {
            "X-RateLimit-Remaining": "999",
            "X-RateLimit-Reset": "0",
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        points = await fetch_price_history(
            mock_client, "0xtoken123", 1700000000, 1700000100
        )

        assert len(points) == 0

    @pytest.mark.asyncio
    async def test_handles_http_error(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.raise_for_status.side_effect = Exception("HTTP 400")
        mock_client.get = AsyncMock(return_value=mock_response)

        points = await fetch_price_history(
            mock_client, "0xtoken123", 1700000000, 1700000100
        )

        assert len(points) == 0


class TestFetchPriceHistoryFallback:
    @pytest.mark.asyncio
    async def test_returns_trades(self):
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.json.return_value = [
            {"price": "0.65", "timestamp": "1700000000"},
            {"price": "0.70", "timestamp": "1700001000"},
        ]
        mock_response.raise_for_status = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        points = await fetch_price_history_fallback(mock_client, "0xtoken123")

        assert len(points) == 2
        assert points[0].p == 0.65

    @pytest.mark.asyncio
    async def test_handles_error_gracefully(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=Exception("Connection error"))

        points = await fetch_price_history_fallback(mock_client, "0xtoken123")

        assert len(points) == 0
