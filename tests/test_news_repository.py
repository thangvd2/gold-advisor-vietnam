import os
import tempfile
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session

from src.storage.models import Base, NewsItem


@pytest.fixture
def news_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(engine)
    yield path, engine
    engine.dispose()
    os.unlink(path)


@pytest.fixture
def async_news_session(news_db):
    path, _ = news_db
    async_engine = create_async_engine(f"sqlite+aiosqlite:///{path}", echo=False)
    session_factory = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    yield session_factory
    import asyncio

    asyncio.get_event_loop().run_until_complete(async_engine.dispose())


class TestNewsItemModel:
    def test_create_news_item(self, news_db):
        path, engine = news_db
        with Session(engine) as session:
            item = NewsItem(
                title="Gold prices surge",
                url="https://example.com/gold",
                source="Reuters",
                is_manual=False,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            assert item.id is not None
            assert item.title == "Gold prices surge"
            assert item.created_at is not None

    def test_manual_flag(self, news_db):
        path, engine = news_db
        with Session(engine) as session:
            item = NewsItem(
                title="SBV auction",
                url="https://sbv.gov.vn/auction",
                source="State Bank",
                is_manual=True,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            assert item.is_manual is True

    def test_optional_fields_default_null(self, news_db):
        path, engine = news_db
        with Session(engine) as session:
            item = NewsItem(
                title="Test",
                url="https://example.com/test",
                source="Test",
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            assert item.published_at is None
            assert item.excerpt is None
            assert item.category is None
            assert item.is_manual is False


class TestNewsRepository:
    @pytest.mark.asyncio
    async def test_save_and_get_recent(self, async_news_session):
        from src.storage.repository import get_recent_news, save_news_item

        session_factory = async_news_session
        async with session_factory() as session:
            for i in range(5):
                await save_news_item(
                    session,
                    title=f"Article {i}",
                    url=f"https://example.com/{i}",
                    source="Test",
                    published_at=datetime.now(timezone.utc),
                )
            await session.commit()

            news = await get_recent_news(session, limit=3)
            assert len(news) == 3

    @pytest.mark.asyncio
    async def test_recent_news_sorted_by_published(self, async_news_session):
        from src.storage.repository import get_recent_news, save_news_item

        session_factory = async_news_session
        async with session_factory() as session:
            now = datetime.now(timezone.utc)
            for i in range(3):
                await save_news_item(
                    session,
                    title=f"Article {i}",
                    url=f"https://example.com/{i}",
                    source="Test",
                    published_at=now - __import__("datetime").timedelta(hours=i),
                )
            await session.commit()

            news = await get_recent_news(session, limit=10)
            for i in range(len(news) - 1):
                assert news[i].published_at >= news[i + 1].published_at

    @pytest.mark.asyncio
    async def test_deduplicate_by_url(self, async_news_session):
        from src.storage.repository import get_recent_news, save_news_item

        session_factory = async_news_session
        async with session_factory() as session:
            await save_news_item(
                session,
                title="First",
                url="https://example.com/dup",
                source="A",
            )
            await save_news_item(
                session,
                title="Second",
                url="https://example.com/dup",
                source="B",
            )
            await session.commit()

            news = await get_recent_news(session, limit=10)
            assert len(news) == 1

    @pytest.mark.asyncio
    async def test_filter_by_category(self, async_news_session):
        from src.storage.repository import get_recent_news, save_news_item

        session_factory = async_news_session
        async with session_factory() as session:
            await save_news_item(
                session,
                title="Gold news",
                url="https://example.com/gold",
                source="A",
                category="gold_market",
            )
            await save_news_item(
                session,
                title="SBV news",
                url="https://example.com/sbv",
                source="B",
                category="state_bank",
            )
            await session.commit()

            news = await get_recent_news(session, limit=10, category="state_bank")
            assert len(news) == 1
            assert news[0].category == "state_bank"

    @pytest.mark.asyncio
    async def test_empty_db_returns_empty_list(self, async_news_session):
        from src.storage.repository import get_recent_news

        session_factory = async_news_session
        async with session_factory() as session:
            news = await get_recent_news(session, limit=10)
            assert news == []
