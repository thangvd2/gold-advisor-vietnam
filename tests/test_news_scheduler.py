import os
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base


@pytest.fixture
def news_scheduler_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)

    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )

    yield path, session_factory

    import asyncio

    asyncio.get_event_loop().run_until_complete(async_engine.dispose())
    engine.dispose()
    os.unlink(path)


RSS_MOCK = b"""<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Fetched news article</title>
      <link>https://feed.example.com/1</link>
      <pubDate>Tue, 25 Mar 2026 10:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>"""


class TestFetchAndStoreNews:
    @pytest.mark.asyncio
    async def test_stores_new_articles(self, news_scheduler_db):
        import httpx
        from unittest.mock import AsyncMock, patch

        path, session_factory = news_scheduler_db

        async def mock_get(url, **kwargs):
            return httpx.Response(
                200, request=httpx.Request("GET", url), content=RSS_MOCK
            )

        with patch("src.ingestion.news.fetcher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = mock_get
            mock_cls.return_value = mock_client

            from src.ingestion.news.store import fetch_and_store_news

            await fetch_and_store_news(
                feeds=[{"url": "https://feed.example.com/rss", "source": "TestFeed"}],
                database_url=f"sqlite+aiosqlite:///{path}",
            )

        from src.storage.repository import get_recent_news

        async with session_factory() as session:
            news = await get_recent_news(session, limit=10)
            assert len(news) == 1
            assert news[0].title == "Fetched news article"

    @pytest.mark.asyncio
    async def test_skips_duplicate_articles(self, news_scheduler_db):
        import httpx
        from unittest.mock import AsyncMock, patch

        path, session_factory = news_scheduler_db

        async def mock_get(url, **kwargs):
            return httpx.Response(
                200, request=httpx.Request("GET", url), content=RSS_MOCK
            )

        with patch("src.ingestion.news.fetcher.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = mock_get
            mock_cls.return_value = mock_client

            from src.ingestion.news.store import fetch_and_store_news

            await fetch_and_store_news(
                feeds=[{"url": "https://feed.example.com/rss", "source": "TestFeed"}],
                database_url=f"sqlite+aiosqlite:///{path}",
            )
            await fetch_and_store_news(
                feeds=[{"url": "https://feed.example.com/rss", "source": "TestFeed"}],
                database_url=f"sqlite+aiosqlite:///{path}",
            )

        from src.storage.repository import get_recent_news

        async with session_factory() as session:
            news = await get_recent_news(session, limit=10)
            assert len(news) == 1

    @pytest.mark.asyncio
    async def test_handles_empty_feed(self, news_scheduler_db):
        path, session_factory = news_scheduler_db

        from src.ingestion.news.store import fetch_and_store_news

        await fetch_and_store_news(
            feeds=[],
            database_url=f"sqlite+aiosqlite:///{path}",
        )

        from src.storage.repository import get_recent_news

        async with session_factory() as session:
            news = await get_recent_news(session, limit=10)
            assert news == []
