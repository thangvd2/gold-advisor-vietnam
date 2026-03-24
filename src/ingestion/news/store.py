import logging

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.ingestion.news.fetcher import NewsFetcher
from src.storage.repository import save_news_item

logger = logging.getLogger(__name__)


async def fetch_and_store_news(
    feeds: list[dict[str, str]],
    database_url: str,
) -> int:
    fetcher = NewsFetcher(feeds=feeds)
    articles = await fetcher.fetch()

    if not articles:
        return 0

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    stored = 0
    try:
        async with session_factory() as session:
            for article in articles:
                result = await save_news_item(
                    session,
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    excerpt=article.excerpt,
                    category=article.category,
                    is_manual=False,
                )
                if result is not None:
                    stored += 1
            await session.commit()
    finally:
        await engine.dispose()

    if stored:
        logger.info(
            "Stored %d new news articles (fetched %d total)", stored, len(articles)
        )

    return stored
