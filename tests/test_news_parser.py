import pytest

from src.ingestion.news.models import NewsArticle
from src.ingestion.news.parser import parse_rss_feed


RSS_20_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Gold Market News</title>
    <link>https://example.com</link>
    <item>
      <title>Gold prices reach new record high</title>
      <link>https://example.com/gold-record</link>
      <pubDate>Tue, 25 Mar 2026 10:00:00 GMT</pubDate>
      <description>Gold prices surged past $3,000 per ounce.</description>
    </item>
    <item>
      <title>State Bank announces gold auction</title>
      <link>https://example.com/sb-auction</link>
      <pubDate>Mon, 24 Mar 2026 08:00:00 GMT</pubDate>
      <description>SBV will hold a gold auction next week.</description>
    </item>
  </channel>
</rss>"""

ATOM_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Economy News</title>
  <link href="https://example.com/feed"/>
  <entry>
    <title>Gold market update</title>
    <link href="https://example.com/gold-update"/>
    <updated>2026-03-25T12:00:00Z</updated>
    <summary>Gold prices stabilized after recent rally.</summary>
  </entry>
  <entry>
    <title>Federal Reserve policy meeting</title>
    <link href="https://example.com/fed-meeting"/>
    <updated>2026-03-24T14:00:00Z</updated>
  </entry>
</feed>"""

RSS_NO_DATES = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article without date</title>
      <link>https://example.com/no-date</link>
    </item>
  </channel>
</rss>"""


class TestParseRSS20:
    def test_parses_rss20_items(self):
        articles = parse_rss_feed(RSS_20_SAMPLE, "GoldMarket")
        assert len(articles) == 2

    def test_extracts_title(self):
        articles = parse_rss_feed(RSS_20_SAMPLE, "GoldMarket")
        assert articles[0].title == "Gold prices reach new record high"

    def test_extracts_url(self):
        articles = parse_rss_feed(RSS_20_SAMPLE, "GoldMarket")
        assert articles[0].url == "https://example.com/gold-record"

    def test_extracts_source(self):
        articles = parse_rss_feed(RSS_20_SAMPLE, "GoldMarket")
        assert articles[0].source == "GoldMarket"

    def test_extracts_published_date(self):
        articles = parse_rss_feed(RSS_20_SAMPLE, "GoldMarket")
        assert articles[0].published_at is not None
        assert articles[0].published_at.year == 2026

    def test_extracts_description_as_excerpt(self):
        articles = parse_rss_feed(RSS_20_SAMPLE, "GoldMarket")
        assert articles[0].excerpt == "Gold prices surged past $3,000 per ounce."

    def test_handles_missing_date(self):
        articles = parse_rss_feed(RSS_NO_DATES, "TestFeed")
        assert len(articles) == 1
        assert articles[0].published_at is None


class TestParseAtom:
    def test_parses_atom_entries(self):
        articles = parse_rss_feed(ATOM_SAMPLE, "EconomyNews")
        assert len(articles) == 2

    def test_extracts_atom_title(self):
        articles = parse_rss_feed(ATOM_SAMPLE, "EconomyNews")
        assert articles[0].title == "Gold market update"

    def test_extracts_atom_link(self):
        articles = parse_rss_feed(ATOM_SAMPLE, "EconomyNews")
        assert articles[0].url == "https://example.com/gold-update"

    def test_extracts_atom_updated_date(self):
        articles = parse_rss_feed(ATOM_SAMPLE, "EconomyNews")
        assert articles[0].published_at is not None
        assert articles[0].published_at.year == 2026

    def test_extracts_atom_summary(self):
        articles = parse_rss_feed(ATOM_SAMPLE, "EconomyNews")
        assert articles[0].excerpt == "Gold prices stabilized after recent rally."

    def test_atom_missing_summary_is_none(self):
        articles = parse_rss_feed(ATOM_SAMPLE, "EconomyNews")
        assert articles[1].excerpt is None

    def test_handles_empty_feed(self):
        empty = b"""<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>"""
        articles = parse_rss_feed(empty, "Empty")
        assert articles == []
