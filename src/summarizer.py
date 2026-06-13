"""Article summarization using an LLM.

Produces tight bullet-point summaries (≤10 bullets, ≤150 words) that
retain all specific figures, names, and examples from the source.
"""

from __future__ import annotations

from src.llm_client import LLMClient
from src.types import Article

_SUMMARIZE_SYSTEM_PROMPT = """\
You are an executive briefing writer. Summarize the given news article \
into a tight bullet-point summary.

RULES:
- ≤10 bullet points
- ≤150 words total
- RETAIN all specific numeric figures (dollar amounts, percentages, \
dates, counts)
- RETAIN specific examples (named products, technologies, initiatives)
- RETAIN specific names (company names, executive names, organization names)
- Strip: greetings, disclaimers, meta-commentary, promotional language
- One idea per bullet point
- Output as plain markdown bullet list (lines starting with "- ")

Return ONLY the bullet points. No intro, no outro, no commentary."""


def summarize_article(article: Article, llm: LLMClient) -> str:
    """Generate a bullet-point summary of an article.

    Args:
        article: Article with full_text populated.
        llm: Configured LLM client.

    Returns:
        Bullet-point summary string, or a fallback message on error.
    """
    content = article.full_text or article.summary
    if not content:
        return "- No content available for summarization."

    user_prompt = (
        f"Title: {article.title}\n\n"
        f"Content:\n{content[:8000]}"
    )

    try:
        bullets = llm.chat(
            system_prompt=_SUMMARIZE_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=1200,
        )
        return bullets
    except RuntimeError:
        return "- Summary generation failed due to API error."
