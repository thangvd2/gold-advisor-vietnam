"""Tests for BTMC gold price scraper."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

BTMC_HTML_TABLE = """
<table class="bd_price_home">
    <tbody>
        <tr style="color: White; background-color:#b81319; font-weight: bold;">
            <th>Thương hiệu</th>
            <th>Loại vàng</th>
            <th>Hàm lượng</th>
            <th>Mua vào</th>
            <th>Bán ra</th>
        </tr>
        <tr>
            <td>VÀNG MIẾNG VRTL BẢO TÍN MINH CHÂU</td>
            <td>999.9 (24k)</td>
            <td>999.9</td>
            <td>16770</td>
            <td>17070</td>
        </tr>
        <tr>
            <td>NHẪN TRÒN TRƠN BẢO TÍN MINH CHÂU</td>
            <td>999.9 (24k)</td>
            <td>999.9</td>
            <td>16770</td>
            <td>17070</td>
        </tr>
        <tr>
            <td>VÀNG MIẾNG SJC</td>
            <td>999.9 (24k)</td>
            <td>999.9</td>
            <td>16720</td>
            <td>17020</td>
        </tr>
        <tr>
            <td>TRANG SỨC VÀNG RỒNG THĂNG LONG 999.9</td>
            <td>999.9 (24k)</td>
            <td>999.9</td>
            <td>16570</td>
            <td>16970</td>
        </tr>
    </tbody>
</table>
"""

BTMC_JSON_RESPONSE = [
    {"type": "VANG_MIENG_SJC", "buy": "16720", "sell": "17020"},
    {"type": "VANG_MIENG_VRTL", "buy": "16770", "sell": "17070"},
    {"type": "NHAN_TRON_VANG_RONG", "buy": "16770", "sell": "17070"},
]


def _make_mock_json_response(data):
    resp = MagicMock()
    resp.json.return_value = data
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


def _make_mock_html_response(html):
    resp = MagicMock()
    resp.text = html
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


class TestBTMCScraper:
    @pytest.mark.asyncio
    async def test_parses_sjc_bar_from_json_api(self):
        """Test 1: Parses JSON response → SJC bar FetchedPrice."""
        mock_response = _make_mock_json_response(BTMC_JSON_RESPONSE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) >= 1
        price = sjc_prices[0]
        assert price.source == "btmc"
        assert price.product_type == "sjc_bar"
        assert price.buy_price is not None
        assert price.buy_price > 0
        assert price.sell_price is not None
        assert price.sell_price > 0
        assert price.sell_price > price.buy_price
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_parses_ring_gold_from_json_api(self):
        """Test 2: Parses ring gold entry → FetchedPrice with product_type='ring_gold'."""
        mock_response = _make_mock_json_response(BTMC_JSON_RESPONSE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        ring_prices = [p for p in results if p.product_type == "ring_gold"]
        assert len(ring_prices) >= 1
        price = ring_prices[0]
        assert price.source == "btmc"
        assert price.product_type == "ring_gold"
        assert price.buy_price is not None
        assert price.buy_price > 0
        assert price.sell_price is not None
        assert price.sell_price > 0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        """Test 3: Returns empty list on httpx network error."""
        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_unexpected_json_structure(self):
        """Test 4: Returns empty list on unexpected JSON structure (missing fields)."""
        bad_json = [{"wrong_field": "value"}]
        json_response = _make_mock_json_response(bad_json)
        empty_html = "<div>No gold data</div>"
        html_response = _make_mock_html_response(empty_html)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()

            call_count = 0

            def get_side(url, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return json_response
                return html_response

            mock_client.get.side_effect = get_side
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_non_200_http_status(self):
        """Test 5: Returns empty list on non-200 HTTP status."""
        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Server Error", request=MagicMock(), response=mock_response
            )
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_falls_back_to_html_when_api_fails(self):
        """Test: Falls back to HTML parsing when JSON API fails."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        call_count = 0

        def side_effect_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if "api.btmc.vn" in url:
                raise httpx.ConnectError("Connection refused")
            return html_response

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = side_effect_get
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        assert len(results) >= 2
        product_types = {p.product_type for p in results}
        assert "sjc_bar" in product_types
        assert "ring_gold" in product_types

    @pytest.mark.asyncio
    async def test_parses_html_sjc_bar_prices(self):
        """Test: Parses SJC bar from HTML table correctly."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()

            def get_side(url, **kwargs):
                if "api.btmc.vn" in url:
                    raise httpx.ConnectError("API fail")
                return html_response

            mock_client.get.side_effect = get_side
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) >= 1

    @pytest.mark.asyncio
    async def test_html_prices_in_correct_unit(self):
        """Test: HTML prices are correctly converted to VND/lượng."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()

            def get_side(url, **kwargs):
                if "api.btmc.vn" in url:
                    raise httpx.ConnectError("API fail")
                return html_response

            mock_client.get.side_effect = get_side
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        vrtl = [p for p in results if "sjc_bar" in p.product_type]
        assert len(vrtl) >= 1
        assert vrtl[0].buy_price > 100_000_000
        assert vrtl[0].sell_price > 100_000_000
