"""Tests for news data models."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.ingestion.news.models import NewsArticle


class TestNewsArticle:
    def test_create_minimal_article(self):
        article = NewsArticle(
            title="Gold prices surge to new high",
            url="https://example.com/gold-surge",
            source="Reuters",
        )
        assert article.title == "Gold prices surge to new high"
        assert article.url == "https://example.com/gold-surge"
        assert article.source == "Reuters"
        assert article.published_at is None
        assert article.excerpt is None
        assert article.category is None

    def test_create_full_article(self):
        now = datetime.now(timezone.utc)
        article = NewsArticle(
            title="Gold prices surge to new high",
            url="https://example.com/gold-surge",
            source="Reuters",
            published_at=now,
            excerpt="Gold prices reached $2,800 per ounce...",
            category="gold_market",
        )
        assert article.title == "Gold prices surge to new high"
        assert article.url == "https://example.com/gold-surge"
        assert article.source == "Reuters"
        assert article.published_at == now
        assert article.excerpt == "Gold prices reached $2,800 per ounce..."
        assert article.category == "gold_market"

    def test_title_required(self):
        with pytest.raises(ValidationError):
            NewsArticle(url="https://example.com", source="test")

    def test_url_required(self):
        with pytest.raises(ValidationError):
            NewsArticle(title="Test", source="test")

    def test_source_required(self):
        with pytest.raises(ValidationError):
            NewsArticle(title="Test", url="https://example.com")

    def test_empty_title_rejected(self):
        with pytest.raises(ValidationError):
            NewsArticle(title="", url="https://example.com", source="test")

    def test_empty_url_rejected(self):
        with pytest.raises(ValidationError):
            NewsArticle(title="Test", url="", source="test")

    def test_published_at_accepts_string(self):
        article = NewsArticle(
            title="Test",
            url="https://example.com",
            source="test",
            published_at="2026-03-25T10:00:00+00:00",
        )
        assert isinstance(article.published_at, datetime)
