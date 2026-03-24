"""Tests for SJC gold price scraper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

SJC_API_RESPONSE = {
    "success": True,
    "latestDate": "14:17 24/03/2026",
    "data": [
        {
            "Id": 1,
            "TypeName": "Vàng SJC 1L, 10L, 1KG",
            "BranchName": "Hồ Chí Minh",
            "Buy": "167,200",
            "BuyValue": 167200000.0,
            "Sell": "170,200",
            "SellValue": 170200000.0,
            "BuyDiffer": None,
            "BuyDifferValue": 0,
            "SellDiffer": None,
            "SellDifferValue": 0,
            "GroupDate": "/Date(-62135596800000)/",
        },
        {
            "Id": 2,
            "TypeName": "Vàng SJC 1L, 10L, 1KG",
            "BranchName": "Miền Bắc",
            "Buy": "167,300",
            "BuyValue": 167300000.0,
            "Sell": "170,300",
            "SellValue": 170300000.0,
            "BuyDiffer": None,
            "BuyDifferValue": 0,
            "SellDiffer": None,
            "SellDifferValue": 0,
            "GroupDate": "/Date(-62135596800000)/",
        },
        {
            "Id": 33,
            "TypeName": "Nữ trang 99,99%",
            "BranchName": "Hồ Chí Minh",
            "Buy": "165,000",
            "BuyValue": 165000000.0,
            "Sell": "168,500",
            "SellValue": 168500000.0,
            "BuyDiffer": None,
            "BuyDifferValue": 0,
            "SellDiffer": None,
            "SellDifferValue": 0,
            "GroupDate": "/Date(-62135596800000)/",
        },
        {
            "Id": 49,
            "TypeName": "Vàng nhẫn SJC 99,99% 1 chỉ, 2 chỉ, 5 chỉ",
            "BranchName": "Hồ Chí Minh",
            "Buy": "167,000",
            "BuyValue": 167000000.0,
            "Sell": "170,000",
            "SellValue": 170000000.0,
            "BuyDiffer": None,
            "BuyDifferValue": 0,
            "SellDiffer": None,
            "SellDifferValue": 0,
            "GroupDate": "/Date(-62135596800000)/",
        },
    ],
}


def _make_mock_json_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


class TestSJCScraper:
    @pytest.mark.asyncio
    async def test_parses_sjc_bar_row(self):
        mock_response = _make_mock_json_response(SJC_API_RESPONSE)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) == 1
        price = sjc_prices[0]
        assert price.source == "sjc"
        assert price.product_type == "sjc_bar"
        assert price.buy_price == 167200000.0
        assert price.sell_price == 170200000.0
        assert price.price_vnd == 167200000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_parses_ring_gold_row(self):
        mock_response = _make_mock_json_response(SJC_API_RESPONSE)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        ring_prices = [p for p in results if p.product_type == "ring_gold"]
        assert len(ring_prices) == 1
        price = ring_prices[0]
        assert price.source == "sjc"
        assert price.product_type == "ring_gold"
        assert price.buy_price == 167000000.0
        assert price.sell_price == 170000000.0
        assert price.price_vnd == 167000000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_uses_buyvalue_sellvalue_directly_no_conversion(self):
        """SJC API returns BuyValue/SellValue already in VND/lượng — no multiplication needed."""
        mock_response = _make_mock_json_response(SJC_API_RESPONSE)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        sjc = [p for p in results if p.product_type == "sjc_bar"][0]
        assert sjc.buy_price == 167200000.0
        assert sjc.sell_price == 170200000.0

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        import httpx

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_price_data_in_response(self):
        empty_response = {"success": True, "latestDate": "", "data": []}
        mock_response = _make_mock_json_response(empty_response)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_parses_timestamp_from_api_response(self):
        mock_response = _make_mock_json_response(SJC_API_RESPONSE)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        for price in results:
            assert price.timestamp is not None
            assert price.timestamp.year == 2026
            assert price.timestamp.month == 3
            assert price.timestamp.day == 24
            assert price.timestamp.hour == 14
            assert price.timestamp.minute == 17

    @pytest.mark.asyncio
    async def test_uses_first_branch_for_duplicate_product_types(self):
        """When multiple branches have same product type, use Hồ Chí Minh (first)."""
        mock_response = _make_mock_json_response(SJC_API_RESPONSE)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) == 1
        assert sjc_prices[0].buy_price == 167200000.0

    @pytest.mark.asyncio
    async def test_defaults_to_utc_now_when_no_timestamp(self):
        no_date_response = {
            "success": True,
            "latestDate": "",
            "data": SJC_API_RESPONSE["data"],
        }
        mock_response = _make_mock_json_response(no_date_response)

        with patch("src.ingestion.scrapers.sjc.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.sjc import SJCScraper

            scraper = SJCScraper()
            results = await scraper.fetch()

        for price in results:
            assert price.timestamp is not None
