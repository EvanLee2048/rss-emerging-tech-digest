"""HKMA relevance filter.

Applies only to articles from the HKMA feed. Filters out operational/
routine announcements, keeping only strategic regulatory items.
Non-HKMA articles are auto-passed.
"""

from __future__ import annotations

import json

from src.llm_client import LLMClient
from src.types import Article

_FILTER_SYSTEM_PROMPT = """\
You are an editorial filter for an executive emerging-tech digest. \
Review HKMA press release items and decide which to KEEP.

KEEP — regulatory circulars on:
- Banking tech risk & operational resilience
- AI governance guidelines
- Fintech policy changes
- Digital asset / stablecoin frameworks
- Cross-border banking initiatives

FILTER OUT (do not include in digest):
- Individual scam alerts or fraud warnings targeting consumers
- Routine statistical data releases (monetary statistics, reserve figures, \
monthly metrics)
- Retirement scheme promotions or product marketing
- Single-bank personnel changes
- Press releases with purely local/operational scope that do not signal \
broader regulatory trends

Respond with ONLY a JSON object:
{"passed": true, "reason": "..."} or {"passed": false, "reason": "..."}
"""


def is_hkma_item(article: Article) -> bool:
    """Check if an article is from the HKMA feed."""
    return article.feed_key == "hkma"


def filter_article(
    article: Article, llm: LLMClient
) -> Article:
    """Apply HKMA relevance filter to a single article.

    Non-HKMA articles are auto-passed without LLM cost.
    """
    article.is_hkma = is_hkma_item(article)

    if not article.is_hkma:
        article.filter_passed = True
        article.filter_reason = "Non-HKMA - auto-passed"
        return article

    # HKMA item — invoke LLM filter
    content_text = article.full_text or article.summary
    if not content_text:
        article.filter_passed = False
        article.filter_reason = "No content to evaluate"
        return article

    try:
        result = llm.chat_json(
            system_prompt=_FILTER_SYSTEM_PROMPT,
            user_prompt=f"Title: {article.title}\n\nContent:\n{content_text[:3000]}",
            temperature=0.1,
            max_tokens=500,
        )
        article.filter_passed = bool(result.get("passed", False))
        article.filter_reason = result.get("reason", "")
    except (RuntimeError, json.JSONDecodeError):
        article.filter_passed = True
        article.filter_reason = "LLM filter failed - article kept by default"

    return article


def filter_all(
    articles: list[Article], llm: LLMClient
) -> list[Article]:
    """Apply HKMA relevance filter to all articles.

    Returns only articles that pass the filter.
    """
    filtered: list[Article] = []
    for article in articles:
        filtered_article = filter_article(article, llm)
        if filtered_article.filter_passed:
            filtered.append(filtered_article)
    return filtered
