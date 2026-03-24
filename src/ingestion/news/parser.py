import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from src.ingestion.news.models import NewsArticle

logger = logging.getLogger(__name__)


def _parse_rfc2822(date_str: str) -> datetime | None:
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(date_str).astimezone(timezone.utc)
    except Exception:
        return None


def _parse_iso8601(date_str: str) -> datetime | None:
    try:
        return datetime.fromisoformat(date_str).astimezone(timezone.utc)
    except Exception:
        return None


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text).strip()


def parse_rss_feed(xml_bytes: bytes, source_name: str) -> list[NewsArticle]:
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        logger.warning("Failed to parse XML from %s", source_name)
        return []

    tag = root.tag

    if tag == "rss" or tag.endswith("}rss"):
        return _parse_rss20(root, source_name)
    elif tag == "feed" or tag.endswith("}feed"):
        return _parse_atom(root, source_name)

    logger.warning("Unknown feed format from %s: %s", source_name, tag)
    return []


def _parse_rss20(root: ET.Element, source_name: str) -> list[NewsArticle]:
    articles = []
    channel = root.find("channel")
    if channel is None:
        return articles

    for item in channel.findall("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        date_el = item.find("pubDate")
        desc_el = item.find("description")

        title = (
            title_el.text.strip() if title_el is not None and title_el.text else None
        )
        link = link_el.text.strip() if link_el is not None and link_el.text else None

        if not title or not link:
            continue

        pub_date = None
        if date_el is not None and date_el.text:
            pub_date = _parse_rfc2822(date_el.text.strip())

        excerpt = None
        if desc_el is not None and desc_el.text:
            excerpt = _strip_html(desc_el.text)[:500]

        articles.append(
            NewsArticle(
                title=title,
                url=link,
                source=source_name,
                published_at=pub_date,
                excerpt=excerpt,
            )
        )

    return articles


def _get_atom_ns(root: ET.Element) -> str:
    if root.tag.startswith("{"):
        return root.tag.split("}")[0] + "}"
    for key, val in root.attrib.items():
        if key == "xmlns" or key.endswith("}xmlns"):
            return f"{{{val}}}"
    return ""


def _find_first(parent: ET.Element, paths: list[str]) -> ET.Element | None:
    for path in paths:
        el = parent.find(path)
        if el is not None:
            return el
    return None


def _parse_atom(root: ET.Element, source_name: str) -> list[NewsArticle]:
    ns = _get_atom_ns(root)

    articles = []
    for entry in root.findall(f"{ns}entry"):
        title_el = entry.find(f"{ns}title")
        link_el = entry.find(f"{ns}link")
        date_el = _find_first(entry, [f"{ns}updated", f"{ns}published"])
        summary_el = _find_first(entry, [f"{ns}summary", f"{ns}content"])

        title = (
            title_el.text.strip() if title_el is not None and title_el.text else None
        )

        link = None
        if link_el is not None:
            link = link_el.get("href", "")

        if not title or not link:
            continue

        pub_date = None
        if date_el is not None and date_el.text:
            pub_date = _parse_iso8601(date_el.text.strip())

        excerpt = None
        if summary_el is not None and summary_el.text:
            excerpt = _strip_html(summary_el.text)[:500]

        articles.append(
            NewsArticle(
                title=title,
                url=link,
                source=source_name,
                published_at=pub_date,
                excerpt=excerpt,
            )
        )

    return articles
