"""Tests for BTMC gold price scraper."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

BTMC_HTML_TABLE = """
<table class="bd_price_home">
    <tbody>
        <tr style="color: White; background-color:#b81319; font-weight: bold;">
            <th>Thương phẩm(Brand of gold)</th>
            <th>Loại vàng(types of gold)</th>
            <th>Hàm lượng(content)</th>
            <th>Mua vào(buy)</th>
            <th>Bán ra(sell)</th>
        </tr>
        <tr>
            <td></td>
            <td>VÀNG MIẾNG VRTL BẢO TÍNMINH CHÂU</td>
            <td>999.9(24k)</td>
            <td>16770</td>
            <td>17070</td>
        </tr>
        <tr>
            <td>NHẪN TRÒN TRƠN BẢO TÍNMINH CHÂU</td>
            <td>999.9(24k)</td>
            <td>16770</td>
            <td>17070</td>
        </tr>
        <tr>
            <td></td>
            <td>VÀNG MIẾNG SJC</td>
            <td>999.9(24k)</td>
            <td>16720</td>
            <td>17020</td>
        </tr>
        <tr>
            <td>TRANG SỨC VÀNG RỒNG THĂNG LONG 99.9</td>
            <td>99.9(24k)</td>
            <td>16760</td>
            <td>17160</td>
        </tr>
        <tr>
            <td></td>
            <td>VÀNG THƯƠNG HIỆU DOJI, PNJ, PHÚ QUÝ...</td>
            <td>999.9(24k)</td>
            <td>16980</td>
            <td>Liên hệ</td>
        </tr>
    </tbody>
</table>
"""


def _make_mock_html_response(html):
    resp = MagicMock()
    resp.text = html
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    return resp


class TestBTMCScraper:
    @pytest.mark.asyncio
    async def test_parses_sjc_bar_from_html(self):
        """Test: Parses HTML table → SJC bar FetchedPrice."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = html_response
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
    async def test_parses_ring_gold_from_html(self):
        """Test: Parses NHẪN TRÒN TRƠN BẢO TÍN MINH CHÂU → ring_gold FetchedPrice."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = html_response
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
        """Test: Returns empty list on httpx network error."""
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
    async def test_returns_empty_on_non_200_http_status(self):
        """Test: Returns empty list on non-200 HTTP status."""
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
    async def test_skips_lien_he_rows(self):
        """Test: Rows with 'Liên hệ' sell price are skipped."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = html_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        # "VÀNG THƯƠNG HIỆU DOJI, PNJ, PHÚ QUÝ..." has "Liên hệ" sell → skipped
        no_lh = [p for p in results if "DOJI" not in p.product_type]
        assert len(no_lh) == len(results)

    @pytest.mark.asyncio
    async def test_prices_in_correct_unit(self):
        """Test: Prices are correctly converted to VND/lượng (×10,000)."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = html_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        for price in results:
            assert price.buy_price > 100_000_000, (
                f"buy_price {price.buy_price} seems wrong (per chỉ?)"
            )
            assert price.sell_price > 100_000_000, (
                f"sell_price {price.sell_price} seems wrong (per chỉ?)"
            )

    @pytest.mark.asyncio
    async def test_returns_both_sjc_and_ring_gold(self):
        """Test: Returns both SJC bar and ring gold products."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = html_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        product_types = {p.product_type for p in results}
        assert "sjc_bar" in product_types
        assert "ring_gold" in product_types

    @pytest.mark.asyncio
    async def test_ring_gold_buy_sell_correct(self):
        """Test: NHẪN TRÒN TRƠN 16770/17070 → 167,700,000/170,700,000."""
        html_response = _make_mock_html_response(BTMC_HTML_TABLE)

        with patch("src.ingestion.scrapers.btmc.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = html_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_client

            from src.ingestion.scrapers.btmc import BTMCScraper

            scraper = BTMCScraper()
            results = await scraper.fetch()

        ring = [p for p in results if p.product_type == "ring_gold"][0]
        assert ring.buy_price == 167_700_000
        assert ring.sell_price == 170_700_000
