"""Tests for PNJ gold price scraper."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PNJ_API_RESPONSE = {
    "data": {
        "updateDate": "24/03/2026 14:15:00",
        "data": [
            {
                "masp": "SJC",
                "tensp": "Vàng miếng SJC 999.9",
                "giaban": 17020,
                "giamua": 16720,
            },
            {
                "masp": "N24K",
                "tensp": "Nhẫn Trơn PNJ 999.9",
                "giaban": 17000,
                "giamua": 16700,
            },
            {
                "masp": "KB",
                "tensp": "Vàng Kim Bảo 999.9",
                "giaban": 17000,
                "giamua": 16700,
            },
            {
                "masp": "24K",
                "tensp": "Vàng nữ trang 999.9",
                "giaban": 16890,
                "giamua": 16490,
            },
            {
                "masp": "999",
                "tensp": "Vàng nữ trang 99.9%",
                "giaban": 16490,
                "giamua": 16090,
            },
        ],
    }
}


def _make_mock_json_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


class TestPNJScraper:
    @pytest.mark.asyncio
    async def test_parses_sjc_bar_row(self):
        mock_response = _make_mock_json_response(PNJ_API_RESPONSE)

        with patch("src.ingestion.scrapers.pnj.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.pnj import PNJScraper

            scraper = PNJScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) == 1
        price = sjc_prices[0]
        assert price.source == "pnj"
        assert price.product_type == "sjc_bar"
        assert price.buy_price == 167200000.0
        assert price.sell_price == 170200000.0
        assert price.price_vnd == 167200000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_parses_ring_gold_row(self):
        mock_response = _make_mock_json_response(PNJ_API_RESPONSE)

        with patch("src.ingestion.scrapers.pnj.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.pnj import PNJScraper

            scraper = PNJScraper()
            results = await scraper.fetch()

        ring_prices = [p for p in results if p.product_type == "ring_gold"]
        assert len(ring_prices) == 1
        price = ring_prices[0]
        assert price.source == "pnj"
        assert price.product_type == "ring_gold"
        assert price.buy_price == 167000000.0
        assert price.sell_price == 170000000.0
        assert price.price_vnd == 167000000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        import httpx

        with patch("src.ingestion.scrapers.pnj.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.pnj import PNJScraper

            scraper = PNJScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_when_react_spa_hasnt_rendered_prices(self):
        empty_response = {"data": {"updateDate": "", "data": []}}
        mock_response = _make_mock_json_response(empty_response)

        with patch("src.ingestion.scrapers.pnj.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.pnj import PNJScraper

            scraper = PNJScraper()
            results = await scraper.fetch()

        assert results == []
