"""Cross-feed semantic deduplication.

Uses an LLM to identify articles from different sources covering the same
news event, keeping only the most authoritative/substantive version.
"""

from __future__ import annotations

import json

from src.llm_client import LLMClient
from src.types import Article

_DEDUP_SYSTEM_PROMPT = """\
You are a news deduplication engine. Given a list of news articles \
collected from multiple RSS sources covering AI, cybersecurity, fintech, \
Web3, and HK regulation, your task:

1. Identify groups of articles covering the same core news event
2. Within each group, KEEP ONLY the article from the most authoritative \
or most substantive source
3. DISCARD the duplicates

RULES:
- Two articles from different outlets about the same product launch, \
research finding, corporate announcement, or regulatory change = duplicate
- Articles that are tangentially related but cover distinct angles are \
NOT duplicates
- Do NOT rely solely on identical URLs
- Compare headlines, key facts, and named entities

Output MUST be a valid JSON object with a single key "kept" containing \
an array of the kept article objects (preserving all original fields)."""


def semantic_dedup(
    articles: list[Article], llm: LLMClient
) -> list[Article]:
    """Deduplicate articles across feeds using LLM semantic analysis.

    Args:
        articles: Articles from all feeds (post-URL-level dedup).
        llm: Configured LLM client.

    Returns:
        Deduplicated list where each unique story appears once.
    """
    if len(articles) <= 1:
        return articles

    # Build a compact representation for the LLM
    items_json = [
        {
            "title": a.title,
            "url": a.url,
            "summary": a.summary[:500] if a.summary else "",
            "feed_key": a.feed_key,
            "feed_label": a.feed_label,
            "category": a.category,
            "url_hash": a.url_hash,
        }
        for a in articles
    ]

    system_prompt = _DEDUP_SYSTEM_PROMPT
    user_prompt = (
        f"Deduplicate this list of {len(articles)} articles. "
        f"Return only the JSON object with 'kept' array:\n\n"
        f"{json.dumps(items_json, indent=2, ensure_ascii=False)}"
    )

    try:
        result = llm.chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.05,
            max_tokens=8000,
        )
    except RuntimeError:
        # On LLM failure, keep all articles rather than dropping them
        return articles

    raw_kept = result.get("kept", []) if isinstance(result, dict) else []
    if not raw_kept:
        return articles

    # Map back to Article objects by url_hash
    hash_map = {a.url_hash: a for a in articles}
    deduped: list[Article] = []
    for kept in raw_kept:
        url_hash = kept.get("url_hash", "")
        if url_hash in hash_map:
            deduped.append(hash_map[url_hash])

    # If LLM returned something broken, safe-fall back to all articles
    return deduped if deduped else articles
