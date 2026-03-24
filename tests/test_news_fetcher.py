import asyncio
from datetime import datetime, timezone

import pytest

from src.ingestion.news.models import NewsArticle

RSS_FEED_A = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Gold up 2%</title>
      <link>https://a.com/1</link>
      <pubDate>Tue, 25 Mar 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Gold down 1%</title>
      <link>https://a.com/2</link>
      <pubDate>Mon, 24 Mar 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""

RSS_FEED_B = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Duplicate from A</title>
      <link>https://a.com/1</link>
      <pubDate>Tue, 25 Mar 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>State Bank auction</title>
      <link>https://b.com/auction</link>
      <pubDate>Tue, 25 Mar 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


@pytest.fixture
def mock_httpx():
    import httpx
    from unittest.mock import AsyncMock, patch

    async def mock_get(url, **kwargs):
        resp = httpx.Response(200, request=httpx.Request("GET", url))
        if "feed-a" in url:
            resp._content = RSS_FEED_A
        elif "feed-b" in url:
            resp._content = RSS_FEED_B
        else:
            resp = httpx.Response(404, request=httpx.Request("GET", url))
        return resp

    with patch("src.ingestion.news.fetcher.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = mock_get
        mock_client_cls.return_value = mock_client
        yield mock_client


class TestNewsFetcher:
    @pytest.mark.asyncio
    async def test_fetches_all_feeds(self, mock_httpx):
        from src.ingestion.news.fetcher import NewsFetcher

        fetcher = NewsFetcher(
            feeds=[
                {"url": "https://example.com/feed-a", "source": "FeedA"},
                {"url": "https://example.com/feed-b", "source": "FeedB"},
            ]
        )
        articles = await fetcher.fetch()
        assert len(articles) == 3

    @pytest.mark.asyncio
    async def test_deduplicates_by_url(self, mock_httpx):
        from src.ingestion.news.fetcher import NewsFetcher

        fetcher = NewsFetcher(
            feeds=[
                {"url": "https://example.com/feed-a", "source": "FeedA"},
                {"url": "https://example.com/feed-b", "source": "FeedB"},
            ]
        )
        articles = await fetcher.fetch()
        urls = [a.url for a in articles]
        assert len(urls) == len(set(urls))

    @pytest.mark.asyncio
    async def test_sorted_newest_first(self, mock_httpx):
        from src.ingestion.news.fetcher import NewsFetcher

        fetcher = NewsFetcher(
            feeds=[
                {"url": "https://example.com/feed-a", "source": "FeedA"},
                {"url": "https://example.com/feed-b", "source": "FeedB"},
            ]
        )
        articles = await fetcher.fetch()
        dated = [a for a in articles if a.published_at]
        for i in range(len(dated) - 1):
            assert dated[i].published_at >= dated[i + 1].published_at

    @pytest.mark.asyncio
    async def test_handles_feed_failure_gracefully(self):
        import httpx
        from unittest.mock import AsyncMock, patch

        async def mock_get_fail(url, **kwargs):
            raise httpx.ConnectError("Connection refused")

        with patch("src.ingestion.news.fetcher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = mock_get_fail
            mock_cls.return_value = mock_client

            from src.ingestion.news.fetcher import NewsFetcher

            fetcher = NewsFetcher(
                feeds=[{"url": "https://bad.example.com/feed", "source": "BadFeed"}]
            )
            articles = await fetcher.fetch()
            assert articles == []

    @pytest.mark.asyncio
    async def test_empty_feed_list(self):
        from src.ingestion.news.fetcher import NewsFetcher

        fetcher = NewsFetcher(feeds=[])
        articles = await fetcher.fetch()
        assert articles == []

    @pytest.mark.asyncio
    async def test_preserves_source_from_config(self, mock_httpx):
        from src.ingestion.news.fetcher import NewsFetcher

        fetcher = NewsFetcher(
            feeds=[{"url": "https://example.com/feed-a", "source": "CustomSource"}]
        )
        articles = await fetcher.fetch()
        assert all(a.source == "CustomSource" for a in articles)
