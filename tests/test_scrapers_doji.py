"""Tests for DOJI gold price scraper."""

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


DOJI_HTML_WITH_PRICES = """
<div class="ant-home-price">
  <table class="goldprice-view">
    <thead><tr><th>Giá vàng trong nước</th><th>Mua</th><th>Bán</th></tr></thead>
    <tbody>
      <tr class="odd">
        <td class="first">
          <span class="title clear-block clear size-18 normal">SJC -Bán Lẻ</span>
          <span class="sub-title clear size-13 normal">(nghìn/chỉ)</span>
        </td>
        <td class="goldprice-td goldprice-td-0"><div class="item-relative">16,720</div></td>
        <td class="goldprice-td goldprice-td-1"><div class="item-relative">17,020</div></td>
      </tr>
      <tr class="even">
        <td class="first">
          <span class="title clear-block clear size-18 normal">Kim TT/AVPL</span>
          <span class="sub-title clear size-13 normal">(nghìn/chỉ)</span>
        </td>
        <td class="goldprice-td goldprice-td-0"><div class="item-relative">16,730</div></td>
        <td class="goldprice-td goldprice-td-1"><div class="item-relative">17,030</div></td>
      </tr>
      <tr class="odd">
        <td class="first">
          <span class="title clear-block clear size-18 normal">NHẪN TRÒN 9999 HƯNG THỊNH VƯỢNG</span>
          <span class="sub-title clear size-13 normal">(nghìn/chỉ)</span>
        </td>
        <td class="goldprice-td goldprice-td-0"><div class="item-relative">16,720</div></td>
        <td class="goldprice-td goldprice-td-1"><div class="item-relative">17,020</div></td>
      </tr>
      <tr class="even">
        <td class="first">
          <span class="title clear-block clear size-18 normal">Nguyên Liệu 99.99</span>
          <span class="sub-title clear size-13 normal"></span>
        </td>
        <td class="goldprice-td goldprice-td-0"><div class="item-relative">15,800</div></td>
        <td class="goldprice-td goldprice-td-1"><div class="item-relative">16,000</div></td>
      </tr>
    </tbody>
  </table>
</div>
<p style="color:#666666"><span class="update-time size-14">Cập nhập lúc: 15:34 24/03/2026</span></p>
"""

DOJI_HTML_EMPTY = "<html><body>No price table here</body></html>"

DOJI_HTML_NO_PRICES = """
<div class="ant-home-price">
  <table class="goldprice-view">
    <tbody>
      <tr class="odd">
        <td class="first"><span class="title">Nguyên Liệu 99.9</span></td>
        <td class="goldprice-td goldprice-td-0"><div class="item-relative">15,750</div></td>
        <td class="goldprice-td goldprice-td-1"><div class="item-relative">15,950</div></td>
      </tr>
    </tbody>
  </table>
</div>
"""


class TestDojiScraper:
    @pytest.mark.asyncio
    async def test_parses_sjc_bar_row(self):
        mock_response = _make_mock_response(DOJI_HTML_WITH_PRICES)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        sjc_prices = [p for p in results if p.product_type == "sjc_bar"]
        assert len(sjc_prices) == 1
        price = sjc_prices[0]
        assert price.source == "doji"
        assert price.product_type == "sjc_bar"
        assert price.buy_price == 167200000.0
        assert price.sell_price == 170200000.0
        assert price.price_vnd == 167200000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_parses_ring_gold_row(self):
        mock_response = _make_mock_response(DOJI_HTML_WITH_PRICES)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        ring_prices = [p for p in results if p.product_type == "ring_gold"]
        assert len(ring_prices) == 1
        price = ring_prices[0]
        assert price.source == "doji"
        assert price.product_type == "ring_gold"
        assert price.buy_price == 167200000.0
        assert price.sell_price == 170200000.0
        assert price.price_vnd == 167200000.0
        assert price.currency == "VND"

    @pytest.mark.asyncio
    async def test_skips_non_target_rows(self):
        mock_response = _make_mock_response(DOJI_HTML_WITH_PRICES)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        assert len(results) == 2
        product_types = {p.product_type for p in results}
        assert product_types == {"sjc_bar", "ring_gold"}

    @pytest.mark.asyncio
    async def test_converts_doji_unit_nghin_chi_to_vnd_luong(self):
        mock_response = _make_mock_response(DOJI_HTML_WITH_PRICES)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        sjc = [p for p in results if p.product_type == "sjc_bar"][0]
        assert sjc.buy_price == 16720 * 10_000
        assert sjc.sell_price == 17020 * 10_000

    @pytest.mark.asyncio
    async def test_returns_empty_on_network_error(self):
        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.TimeoutException("timeout")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_returns_empty_on_malformed_html(self):
        mock_response = _make_mock_response(DOJI_HTML_EMPTY)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        assert results == []

    @pytest.mark.asyncio
    async def test_parses_update_timestamp(self):
        mock_response = _make_mock_response(DOJI_HTML_WITH_PRICES)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        for price in results:
            assert price.timestamp is not None
            assert price.timestamp.year == 2026
            assert price.timestamp.month == 3
            assert price.timestamp.day == 24
            assert price.timestamp.hour == 15
            assert price.timestamp.minute == 34

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_target_products_found(self):
        mock_response = _make_mock_response(DOJI_HTML_NO_PRICES)

        with patch("src.ingestion.scrapers.doji.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_response
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client_cls.return_value = mock_client

            from src.ingestion.scrapers.doji import DojiScraper

            scraper = DojiScraper()
            results = await scraper.fetch()

        assert results == []
