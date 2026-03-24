from fastapi import APIRouter, HTTPException, Query

from src.config import Settings
from src.storage.database import async_session
from src.storage.models import NewsItem
from src.storage.repository import get_recent_news

router = APIRouter()


def get_settings() -> Settings:
    return Settings()


@router.get("")
async def list_news(
    limit: int = Query(20, ge=1, le=50),
    category: str | None = Query(None),
):
    async with async_session() as session:
        news = await get_recent_news(session, limit=limit, category=category)

    return [
        {
            "id": n.id,
            "title": n.title,
            "url": n.url,
            "source": n.source,
            "published_at": n.published_at.isoformat() if n.published_at else None,
            "excerpt": n.excerpt,
            "category": n.category,
            "is_manual": n.is_manual,
        }
        for n in news
    ]


@router.get("/{news_id}")
async def get_news_item(news_id: int):
    async with async_session() as session:
        from sqlalchemy import select

        stmt = select(NewsItem).where(NewsItem.id == news_id)
        result = await session.execute(stmt)
        item = result.scalar_one_or_none()

    if item is None:
        raise HTTPException(status_code=404, detail="News item not found")

    return {
        "id": item.id,
        "title": item.title,
        "url": item.url,
        "source": item.source,
        "published_at": item.published_at.isoformat() if item.published_at else None,
        "excerpt": item.excerpt,
        "category": item.category,
        "is_manual": item.is_manual,
    }
