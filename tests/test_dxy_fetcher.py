"""Tests for DXY (US Dollar Index) fetcher."""

from datetime import datetime, timezone

import pytest
from unittest.mock import MagicMock, patch

from src.ingestion.models import FetchedPrice


class TestDXYFetcherReturnsData:
    @pytest.mark.asyncio
    async def test_fetch_returns_fetched_price_with_dxy_data(self):
        """DXYFetcher.fetch() returns FetchedPrice with product_type='dxy'."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 104.5

        with patch("src.ingestion.fetchers.dxy.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            from src.ingestion.fetchers.dxy import DXYFetcher

            fetcher = DXYFetcher()
            results = await fetcher.fetch()

        assert len(results) == 1
        price = results[0]
        assert isinstance(price, FetchedPrice)
        assert price.source == "yfinance"
        assert price.product_type == "dxy"
        assert price.price_usd == 104.5
        assert price.currency == "USD"
        assert price.timestamp is not None


class TestDXYFetcherErrorHandling:
    @pytest.mark.asyncio
    async def test_fetch_handles_network_error(self):
        """DXYFetcher returns empty list on network error."""
        with patch("src.ingestion.fetchers.dxy.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            from src.ingestion.fetchers.dxy import DXYFetcher

            fetcher = DXYFetcher()
            results = await fetcher.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_handles_none_price(self):
        """DXYFetcher returns empty list when price is None."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = None

        with patch("src.ingestion.fetchers.dxy.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            from src.ingestion.fetchers.dxy import DXYFetcher

            fetcher = DXYFetcher()
            results = await fetcher.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_handles_zero_price(self):
        """DXYFetcher returns empty list when price is zero."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 0.0

        with patch("src.ingestion.fetchers.dxy.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            from src.ingestion.fetchers.dxy import DXYFetcher

            fetcher = DXYFetcher()
            results = await fetcher.fetch()

        assert results == []
