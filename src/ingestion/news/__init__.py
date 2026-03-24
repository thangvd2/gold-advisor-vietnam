from datetime import datetime

from pydantic import BaseModel, Field


class NewsArticle(BaseModel):
    title: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    source: str = Field(..., min_length=1)
    published_at: datetime | None = None
    excerpt: str | None = None
    category: str | None = None
