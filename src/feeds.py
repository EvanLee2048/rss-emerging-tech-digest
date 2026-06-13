"""RSS feed fetching and parsing.

Fetches XML from configured RSS/Atom feed URLs and parses them into
Article objects. Handles both RSS 2.0 (<item>) and Atom (<entry>) formats.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.types import ALL_FEEDS, Article, CATEGORY_MAP, FeedConfig

# Common RSS date formats
_RSS_DATE_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",     # Mon, 01 Jan 2024 12:00:00 +0000
    "%a, %d %b %Y %H:%M:%S %Z",     # Mon, 01 Jan 2024 12:00:00 GMT
    "%d %b %Y %H:%M:%S %z",         # 01 Jan 2024 12:00:00 +0000
    "%Y-%m-%dT%H:%M:%S%z",          # 2024-01-01T12:00:00+00:00 (ISO 8601)
    "%Y-%m-%dT%H:%M:%SZ",           # 2024-01-01T12:00:00Z
    "%Y-%m-%d %H:%M:%S",            # 2024-01-01 12:00:00
]


def _parse_date(date_str: Optional[str]) -> str:
    """Parse a date string from RSS/Atom and return YYYY-MM-DD format.

    Returns empty string if parsing fails.
    """
    if not date_str:
        return ""
    date_str = date_str.strip()
    for fmt in _RSS_DATE_FORMATS:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # Last resort: try to extract YYYY-MM-DD substring
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
    return m.group(1) if m else ""


def _strip_ns(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _parse_rss_items(root: ET.Element, feed_cfg: FeedConfig) -> list[Article]:
    """Parse RSS 2.0 <item> elements."""
    articles: list[Article] = []
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    is_atom = root.tag == "{http://www.w3.org/2005/Atom}feed"

    if is_atom:
        for entry in root.findall(".//atom:entry", ns):
            title_el = entry.find("atom:title", ns)
            link_el = entry.find("atom:link", ns)
            summary_el = entry.find("atom:summary", ns)
            id_el = entry.find("atom:id", ns)
            published_el = entry.find("atom:published", ns)
            updated_el = entry.find("atom:updated", ns)
            url = (link_el.get("href", "") if link_el is not None else "").strip()
            guid = (id_el.text or "").strip() if id_el is not None else url
            date_str = _parse_date(
                (published_el.text if published_el is not None else None)
                or (updated_el.text if updated_el is not None else None)
            )
            articles.append(
                Article(
                    title=(title_el.text or "").strip() if title_el is not None else "",
                    url=url,
                    summary=(summary_el.text or "").strip() if summary_el is not None else "",
                    guid=guid or url,
                    date=date_str,
                    feed_key=feed_cfg.watcher_name,
                    feed_label=feed_cfg.label,
                    category=CATEGORY_MAP.get(feed_cfg.category, "Other"),
                )
            )
    else:
        for item in root.iter("item"):
            title_el = item.find("title")
            link_el = item.find("link")
            desc_el = item.find("description")
            guid_el = item.find("guid")
            pubdate_el = item.find("pubDate")
            url = (link_el.text or "").strip() if link_el is not None else ""
            guid = (guid_el.text or "").strip() if guid_el is not None else url
            date_str = _parse_date(
                pubdate_el.text if pubdate_el is not None else None
            )
            articles.append(
                Article(
                    title=(title_el.text or "").strip() if title_el is not None else "",
                    url=url,
                    summary=(desc_el.text or "").strip() if desc_el is not None else "",
                    guid=guid or url,
                    date=date_str,
                    feed_key=feed_cfg.watcher_name,
                    feed_label=feed_cfg.label,
                    category=CATEGORY_MAP.get(feed_cfg.category, "Other"),
                )
            )
    return articles


def fetch_feed(feed_cfg: FeedConfig, timeout: int = 20) -> Optional[list[Article]]:
    """Fetch and parse a single RSS/Atom feed.

    Returns a list of Article objects, or None on error.
    """
    try:
        req = Request(
            feed_cfg.url,
            headers={"User-Agent": "Hermes-Digest/1.0"},
        )
        with urlopen(req, timeout=timeout) as resp:
            xml_bytes = resp.read()
    except (HTTPError, URLError, TimeoutError, OSError):
        return None

    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError:
        return None

    articles = _parse_rss_items(root, feed_cfg)

    # Filter out empty entries
    return [a for a in articles if a.url and (a.title or a.summary)]


def get_feeds(category_filter: Optional[str] = None) -> list[FeedConfig]:
    """Return the list of feeds, optionally filtered by category.

    Args:
        category_filter: One of 'ai', 'cyber', 'fintech', 'web3', 'hkma',
            or None for all feeds.
    """
    if category_filter is None or category_filter == "all":
        return list(ALL_FEEDS)
    return [f for f in ALL_FEEDS if f.category == category_filter]
