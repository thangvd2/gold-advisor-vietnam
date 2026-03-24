"""Tests for ingestion models, DataSource base, and YFinanceGoldFetcher."""

from datetime import datetime, timezone

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ingestion.models import FetchedPrice, convert_usd_to_vnd_per_luong
from src.ingestion.fetchers.base import DataSource


# ── FetchedPrice model tests ──────────────────────────────────────────────────


class TestFetchedPrice:
    def test_valid_fetched_price(self):
        price = FetchedPrice(
            source="yfinance",
            product_type="xau_usd",
            buy_price=2650.0,
            sell_price=2651.0,
            price_usd=2650.5,
            currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        assert price.source == "yfinance"
        assert price.product_type == "xau_usd"
        assert price.buy_price == 2650.0
        assert price.sell_price == 2651.0
        assert price.price_usd == 2650.5
        assert price.currency == "USD"
        assert price.fetched_at is not None

    def test_rejects_price_zero(self):
        with pytest.raises(Exception):
            FetchedPrice(
                source="yfinance",
                product_type="xau_usd",
                buy_price=0.0,
                currency="USD",
                timestamp=datetime.now(timezone.utc),
            )

    def test_rejects_negative_price(self):
        with pytest.raises(Exception):
            FetchedPrice(
                source="yfinance",
                product_type="xau_usd",
                price_usd=-100.0,
                currency="USD",
                timestamp=datetime.now(timezone.utc),
            )

    def test_none_prices_accepted(self):
        price = FetchedPrice(
            source="test",
            product_type="test",
            currency="USD",
            timestamp=datetime.now(timezone.utc),
        )
        assert price.buy_price is None
        assert price.sell_price is None
        assert price.price_usd is None
        assert price.price_vnd is None


# ── DataSource ABC tests ──────────────────────────────────────────────────────


class TestDataSource:
    def test_cannot_instantiate_abstract_class(self):
        with pytest.raises(TypeError):
            DataSource()

    def test_subclass_must_implement_fetch(self):
        class IncompleteSource(DataSource):
            pass

        with pytest.raises(TypeError):
            IncompleteSource()

    def test_concrete_subclass_works(self):
        class DummySource(DataSource):
            async def fetch(self) -> list[FetchedPrice]:
                return []

        source = DummySource()
        assert source is not None


# ── YFinanceGoldFetcher tests ─────────────────────────────────────────────────


class TestYFinanceGoldFetcher:
    @pytest.mark.asyncio
    async def test_fetch_returns_fetched_price(self):
        """YFinanceGoldFetcher.fetch() returns FetchedPrice with correct fields."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = 2650.5
        mock_ticker.fast_info.previous_close = 2648.0

        with patch("src.ingestion.fetchers.gold_price.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            from src.ingestion.fetchers.gold_price import YFinanceGoldFetcher

            fetcher = YFinanceGoldFetcher()
            results = await fetcher.fetch()

        assert len(results) >= 1
        price = results[0]
        assert isinstance(price, FetchedPrice)
        assert price.source == "yfinance"
        assert price.product_type == "xau_usd"
        assert price.currency == "USD"
        assert price.price_usd is not None
        assert price.price_usd > 0
        assert price.timestamp is not None

    @pytest.mark.asyncio
    async def test_fetch_handles_network_errors(self):
        """YFinanceGoldFetcher handles errors gracefully — returns empty list."""
        with patch("src.ingestion.fetchers.gold_price.yf") as mock_yf:
            mock_yf.Ticker.side_effect = Exception("Network error")
            from src.ingestion.fetchers.gold_price import YFinanceGoldFetcher

            fetcher = YFinanceGoldFetcher()
            results = await fetcher.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_fetch_handles_empty_data(self):
        """YFinanceGoldFetcher returns empty list when yfinance returns no data."""
        mock_ticker = MagicMock()
        mock_ticker.fast_info.last_price = None
        mock_ticker.fast_info.previous_close = None
        mock_ticker.history.return_value.empty = True

        with patch("src.ingestion.fetchers.gold_price.yf") as mock_yf:
            mock_yf.Ticker.return_value = mock_ticker
            from src.ingestion.fetchers.gold_price import YFinanceGoldFetcher

            fetcher = YFinanceGoldFetcher()
            results = await fetcher.fetch()

        assert results == []


# ── Conversion function tests ─────────────────────────────────────────────────


class TestConversion:
    def test_usd_to_vnd_per_luong(self):
        usd_per_oz = 2000.0
        vnd_per_usd = 25000.0
        result = convert_usd_to_vnd_per_luong(usd_per_oz, vnd_per_usd)
        expected = (usd_per_oz / 31.1034768) * 37.5 * vnd_per_usd
        assert abs(result - expected) < 0.01

    def test_conversion_factor(self):
        usd_per_oz = 1000.0
        vnd_per_usd = 25000.0
        result = convert_usd_to_vnd_per_luong(usd_per_oz, vnd_per_usd)
        expected = (usd_per_oz / 31.1034768) * 37.5 * vnd_per_usd
        assert abs(result - expected) < 0.01

    def test_round_trip_consistency(self):
        usd_per_oz = 2650.0
        vnd_per_usd = 25500.0
        vnd_per_luong = convert_usd_to_vnd_per_luong(usd_per_oz, vnd_per_usd)
        recovered = (vnd_per_luong * (31.1034768 / 37.5)) / vnd_per_usd
        assert abs(recovered - usd_per_oz) < 0.01
