from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.storage.database import async_session
from src.storage.models import NewsItem, PolicyEvent
from src.storage.repository import save_news_item

router = APIRouter()

VALID_EVENT_TYPES = {
    "import_approval",
    "auction",
    "intervention",
    "regulation_change",
    "inspection",
}
VALID_IMPACTS = {"bullish", "bearish", "neutral", "uncertain"}
VALID_SEVERITIES = {"high", "medium", "low"}


class ManualNewsCreate(BaseModel):
    title: str = Field(..., min_length=1)
    url: str | None = None
    source: str = Field(..., min_length=1)
    published_at: str | None = None
    excerpt: str | None = None
    category: str | None = "state_bank"


class PolicyEventCreate(BaseModel):
    event_type: str = Field(
        ...,
        pattern="^(import_approval|auction|intervention|regulation_change|inspection)$",
    )
    description: str = Field(..., min_length=1)
    impact: str = Field(..., pattern="^(bullish|bearish|neutral|uncertain)$")
    severity: str = Field(..., pattern="^(high|medium|low)$")
    effective_date: str
    expires_at: str | None = None


@router.post("/policy-events")
async def create_policy_event(body: PolicyEventCreate):
    effective_date = datetime.fromisoformat(body.effective_date)
    expires_at = None
    if body.expires_at:
        expires_at = datetime.fromisoformat(body.expires_at)

    async with async_session() as session:
        event = PolicyEvent(
            event_type=body.event_type,
            description=body.description,
            impact=body.impact,
            severity=body.severity,
            effective_date=effective_date,
            expires_at=expires_at,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

    return {
        "id": event.id,
        "event_type": event.event_type,
        "description": event.description,
        "impact": event.impact,
        "severity": event.severity,
        "effective_date": event.effective_date.isoformat()
        if event.effective_date
        else None,
        "expires_at": event.expires_at.isoformat() if event.expires_at else None,
        "is_active": event.is_active,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }


@router.post("/news")
async def create_manual_news(body: ManualNewsCreate):
    published_at = None
    if body.published_at:
        published_at = datetime.fromisoformat(body.published_at)

    url = body.url or f"manual://{body.title[:50].replace(' ', '-').lower()}"

    async with async_session() as session:
        item = await save_news_item(
            session,
            title=body.title,
            url=url,
            source=body.source,
            published_at=published_at,
            excerpt=body.excerpt,
            category=body.category,
            is_manual=True,
        )
        await session.commit()
        if item:
            await session.refresh(item)

    if item is None:
        return {"status": "duplicate", "url": url}

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


@router.get("/policy-events")
async def list_policy_events(active_only: bool = Query(False)):
    async with async_session() as session:
        stmt = select(PolicyEvent).order_by(PolicyEvent.created_at.desc())
        if active_only:
            stmt = stmt.where(PolicyEvent.is_active.is_(True))
        result = await session.execute(stmt)
        events = result.scalars().all()

    return [
        {
            "id": e.id,
            "event_type": e.event_type,
            "description": e.description,
            "impact": e.impact,
            "severity": e.severity,
            "effective_date": e.effective_date.isoformat()
            if e.effective_date
            else None,
            "expires_at": e.expires_at.isoformat() if e.expires_at else None,
            "is_active": e.is_active,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in events
    ]


@router.delete("/policy-events/{event_id}")
async def deactivate_policy_event(event_id: int):
    async with async_session() as session:
        stmt = select(PolicyEvent).where(PolicyEvent.id == event_id)
        result = await session.execute(stmt)
        event = result.scalar_one_or_none()

        if event is None:
            raise HTTPException(status_code=404, detail="Policy event not found")

        event.is_active = False
        await session.commit()
        await session.refresh(event)

    return {
        "id": event.id,
        "event_type": event.event_type,
        "description": event.description,
        "impact": event.impact,
        "severity": event.severity,
        "effective_date": event.effective_date.isoformat()
        if event.effective_date
        else None,
        "expires_at": event.expires_at.isoformat() if event.expires_at else None,
        "is_active": event.is_active,
        "created_at": event.created_at.isoformat() if event.created_at else None,
    }
