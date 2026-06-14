"""Full-article content fetching with Jina fallback.

Strategy (tiered):
1. Direct HTTP fetch to the article URL (works for most open sites)
2. Jina AI Reader proxy — used only when direct access is blocked by
   Cloudflare/WAF, or when running on cloud infrastructure where
   sites commonly block datacenter IPs
3. RSS-level summary text — last resort
"""

from __future__ import annotations

import urllib.parse
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.types import Article


JINA_BASE = "https://r.jina.ai"

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]


def _direct_fetch(url: str, timeout: int) -> Optional[str]:
    """Try fetching the article URL directly.

    Returns the text content on success, or None if the page appears
    blocked (short content, captcha walls, etc.).
    """
    for ua in _USER_AGENTS:
        try:
            req = Request(
                url,
                headers={
                    "User-Agent": ua,
                    "Accept": "text/html,application/xhtml+xml",
                    "Accept-Language": "en-US,en;q=0.9",
                },
            )
            with urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            # If we got substantive content, use it
            if len(text.strip()) >= 200:
                return text
        except (HTTPError, URLError, TimeoutError, OSError):
            continue
    return None


def _jina_fetch(url: str, timeout: int) -> Optional[str]:
    """Fetch full article content via Jina AI Reader proxy.

    Jina bypasses Cloudflare and bot detection for most sources.
    Returns None on failure.
    """
    jina_url = f"{JINA_BASE}/{urllib.parse.quote(url, safe='')}"
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
        # Jina may return "Warning: ..." for blocked pages
        if text.startswith("Warning:") or len(text.strip()) < 100:
            return None
        return text
    except (HTTPError, URLError, TimeoutError, OSError):
        return None


def fetch_full_text(
    article: Article, timeout: int = 30, jina_only: bool = False
) -> str:
    """Fetch full article content.

    Strategy:
    1. Direct HTTP fetch to the article URL (skipped if jina_only=True)
    2. Jina AI Reader proxy (if direct access fails or jina_only=True)
    3. RSS-level summary text (last resort)

    Args:
        article: Article to fetch content for.
        timeout: HTTP timeout in seconds.
        jina_only: If True, skip direct fetch and use Jina proxy directly.

    Returns:
        The full article text, or the RSS summary fallback on error.
    """
    if not article.url:
        return article.summary

    # Tier 1: Direct fetch (skip if jina_only)
    if not jina_only:
        text = _direct_fetch(article.url, timeout)
        if text is not None:
            return text

    # Tier 2: Jina proxy
    text = _jina_fetch(article.url, timeout)
    if text is not None:
        return text

    # Tier 3: RSS summary fallback
    return article.summary


def enrich_article(
    article: Article, timeout: int = 30, jina_only: bool = False
) -> Article:
    """Fetch full text and return the enriched article.

    Args:
        article: Article to enrich.
        timeout: HTTP timeout in seconds.
        jina_only: If True, skip direct fetch and use Jina proxy directly.
    """
    full_text = fetch_full_text(article, timeout=timeout, jina_only=jina_only)
    article.full_text = full_text
    return article
