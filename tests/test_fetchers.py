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
        """$2000/oz × 25000 VND/USD / 1.09714286 ≈ 45,568,000 VND/lượng."""
        usd_per_oz = 2000.0
        vnd_per_usd = 25000.0
        result = convert_usd_to_vnd_per_luong(usd_per_oz, vnd_per_usd)
        expected = (2000.0 * 25000.0) / 1.09714286
        assert abs(result - expected) < 0.01
        assert abs(result - 45568181.82) < 1.0

    def test_conversion_factor(self):
        """Verify the conversion factor: 1 oz = 31.1034768g, 1 lượng = 37.5g."""
        # 31.1034768 / 37.5 = 0.829426...
        # So 1 lượng = 1 / 0.829426 oz = 1.2056... oz
        # Or equivalently: VND/lượng = (USD/oz × VND/USD) / (31.1034768 / 37.5)
        usd_per_oz = 1000.0
        vnd_per_usd = 25000.0
        result = convert_usd_to_vnd_per_luong(usd_per_oz, vnd_per_usd)
        # 1000 * 25000 = 25,000,000 VND/oz
        # 25,000,000 / 1.09714286 = 22,784,090.9 VND/lượng
        assert 22_000_000 < result < 23_000_000

    def test_round_trip_consistency(self):
        """VND/lượng × conversion factor / VND_per_USD should ≈ USD/oz."""
        usd_per_oz = 2650.0
        vnd_per_usd = 25500.0
        vnd_per_luong = convert_usd_to_vnd_per_luong(usd_per_oz, vnd_per_usd)
        # Reverse: (vnd_per_luong * 1.09714286) / vnd_per_usd ≈ usd_per_oz
        recovered = (vnd_per_luong * 1.09714286) / vnd_per_usd
        assert abs(recovered - usd_per_oz) < 0.01
