"""Full-article content fetching via Jina AI Reader proxy.

Fetches rendered plain text from article URLs using Jina's proxy service,
which bypasses Cloudflare and bot detection for most sources.

Fallback: if Jina returns an error, uses the RSS-level summary text.
"""

from __future__ import annotations

import urllib.parse
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.types import Article


JINA_BASE = "https://r.jina.ai"


def fetch_full_text(article: Article, timeout: int = 30) -> str:
    """Fetch full article content via Jina proxy.

    Returns:
        The full article text, or the RSS summary fallback on error.
    """
    if not article.url:
        return article.summary

    jina_url = f"{JINA_BASE}/{urllib.parse.quote(article.url, safe='')}"
    try:
        req = Request(
            jina_url,
            headers={
                "User-Agent": "curl/8.0",
                "X-No-Images": "true",
                "X-Return-Format": "text",
            },
        )
        with urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8", errors="replace")
        # Jina may return "Warning: ..." for blocked pages — fallback if so
        if text.startswith("Warning:") or len(text.strip()) < 100:
            return article.summary
        return text
    except (HTTPError, URLError, TimeoutError, OSError):
        return article.summary


def enrich_article(article: Article, timeout: int = 30) -> Article:
    """Fetch full text and return the enriched article."""
    full_text = fetch_full_text(article, timeout=timeout)
    article.full_text = full_text
    return article
