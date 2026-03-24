import asyncio
import logging

import httpx

from src.ingestion.news.models import NewsArticle
from src.ingestion.news.parser import parse_rss_feed

logger = logging.getLogger(__name__)


class NewsFetcher:
    def __init__(self, feeds: list[dict[str, str]]):
        self.feeds = feeds

    async def _fetch_single_feed(
        self, client: httpx.AsyncClient, feed: dict[str, str]
    ) -> list[NewsArticle]:
        url = feed["url"]
        source = feed.get("source", url)
        try:
            resp = await client.get(url, timeout=15.0)
            resp.raise_for_status()
            return parse_rss_feed(resp.content, source)
        except Exception:
            logger.exception("Failed to fetch news from %s", url)
            return []

    async def fetch(self) -> list[NewsArticle]:
        if not self.feeds:
            return []

        async with httpx.AsyncClient() as client:
            tasks = [self._fetch_single_feed(client, f) for f in self.feeds]
            results = await asyncio.gather(*tasks)

        all_articles = []
        for articles in results:
            all_articles.extend(articles)

        seen_urls = set()
        unique = []
        for article in all_articles:
            if article.url not in seen_urls:
                seen_urls.add(article.url)
                unique.append(article)

        unique.sort(
            key=lambda a: a.published_at or asyncio.get_event_loop().time(),
            reverse=True,
        )
        return unique
