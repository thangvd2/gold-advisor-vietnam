"""Tests for Phú Quý gold price scraper."""

import httpx
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.ingestion.models import FetchedPrice


def _make_mock_response(html: str) -> MagicMock:
    resp = MagicMock()
    resp.text = html
    resp.raise_for_status = MagicMock()
    return resp


PHUQUY_HTML_WITH_PRICES = """
<div id="lastupdate" class="mb-3">
    <p class="update-time">Gi&#225; v&#224;ng cập nhật lần cuối l&#250;c 18:23 24/03/2026</p>
</div>
<div id="priceList">
    <table class="m-auto text-center">
        <thead>
            <tr>
                <th class="table-price-cell beautique">Loại vàng</th>
                <th class="py-3">
                    <p class="m-0 table-price-cell beautique">Mua vào</p>
                    <p class="m-0 fw-light">(VNĐ/Chỉ)</p>
                </th>
                <th class="py-3">
                    <p class="m-0 table-price-cell beautique">Bán ra</p>
                    <p class="m-0 fw-light">(VNĐ/Chỉ)</p>
                </th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td class="text-center">V&#224;ng miếng SJC</td>
                <td class="text-center table-price-cell another-price-cell buy-price">16,720,000</td>
                <td class="text-center table-price-cell another-price-cell sell-price">17,020,000</td>
            </tr>
            <tr>
                <td class="text-center">Nhẫn tr&#242;n Ph&#250; Qu&#253; 999.9</td>
                <td class="text-center table-price-cell another-price-cell buy-price">16,720,000</td>
                <td class="text-center table-price-cell another-price-cell sell-price">17,020,000</td>
            </tr>
            <tr>
                <td class="text-center">Ph&#250; Qu&#253; 1 Lượng 999.9</td>
                <td class="text-center table-price-cell another-price-cell buy-price">16,720,000</td>
                <td class="text-center table-price-cell another-price-cell sell-price">17,020,000</td>
            </tr>
            <tr>
                <td class="text-center">V&#224;ng trang sức 999.9</td>
                <td class="text-center table-price-cell another-price-cell buy-price">16,450,000</td>
                <td class="text-center table-price-cell another-price-cell sell-price">16,850,000</td>
            </tr>
        </tbody>
    </table>
</div>
"""

PHUQUY_HTML_EMPTY = "<html><body>No price table here</body></html>"


class TestPhuQuyScraper:
    @pytest.mark.asyncio
    async def test_parses_sjc_bar_row(self):
        mock_response = _make_mock_response(PHUQUY_HTML_WITH_PRICES)

        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) == 1
        price = sjc_prices[0]
        assert price.source == "phuquy"
        assert price.product_type == "sjc_bar"
        assert price.buy_price == 167200000.0
        assert price.sell_price == 170200000.0
        assert price.price_vnd == 167200000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_parses_ring_gold_row(self):
        mock_response = _make_mock_response(PHUQUY_HTML_WITH_PRICES)

        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        ring_prices = [p for p in results if p.product_type == "ring_gold"]
        assert len(ring_prices) == 1
        price = ring_prices[0]
        assert price.source == "phuquy"
        assert price.product_type == "ring_gold"
        assert price.buy_price == 167200000.0
        assert price.sell_price == 170200000.0
        assert price.price_vnd == 167200000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_converts_phuquy_unit_vnd_chi_to_vnd_luong(self):
        mock_response = _make_mock_response(PHUQUY_HTML_WITH_PRICES)

        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        sjc = [p for p in results if p.product_type == "sjc_bar"][0]
        assert sjc.buy_price == 16720000.0 * 10
        assert sjc.sell_price == 17020000.0 * 10

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_handles_thousand_separators(self):
        mock_response = _make_mock_response(PHUQUY_HTML_WITH_PRICES)

        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        assert len(results) == 2
        for price in results:
            assert price.buy_price > 0
            assert price.sell_price > 0

    @pytest.mark.asyncio
    async def test_returns_empty_on_malformed_html(self):
        mock_response = _make_mock_response(PHUQUY_HTML_EMPTY)

        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_parses_update_timestamp(self):
        mock_response = _make_mock_response(PHUQUY_HTML_WITH_PRICES)

        with patch(
            "src.ingestion.scrapers.phuquy.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.phuquy import PhuQuyScraper

            scraper = PhuQuyScraper()
            results = await scraper.fetch()

        for price in results:
            assert price.timestamp is not None
            assert price.timestamp.year == 2026
            assert price.timestamp.month == 3
            assert price.timestamp.day == 24
            assert price.timestamp.hour == 18
            assert price.timestamp.minute == 23
