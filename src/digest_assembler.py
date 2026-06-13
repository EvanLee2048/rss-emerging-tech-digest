"""Final digest assembly.

Formats the processed articles into the structured Emerging Tech Digest
output. Follows the user's tone and formatting preferences: professional
executive tone, PM-style language, point form, no fluff.
"""

from __future__ import annotations

from src.types import Article, CATEGORY_MAP


def _format_article_block(article: Article) -> str:
    """Format a single article block (title, source, summary, briefing)."""
    lines: list[str] = []

    # Title (wrapped in brackets per the digest format)
    lines.append(f"[{article.title}]")
    date_part = f" | {article.date}" if article.date else ""
    lines.append(
        f"Source: {article.feed_label} | Link: {article.url}{date_part}"
    )

    # Bullet summary
    if article.bullets:
        lines.append("")
        lines.append(article.bullets)

    # Director Briefing
    if article.director_briefing:
        lines.append("")
        lines.append(article.director_briefing)

    lines.append("")
    return "\n".join(lines)


def assemble_digest(
    articles: list[Article],
    feeds_scanned: int,
    categories_with_new: list[str],
) -> str:
    """Assemble the full Emerging Tech Digest text.

    Args:
        articles: Processed articles (with bullets and briefing populated).
        feeds_scanned: Number of feeds scanned in this run.
        categories_with_new: Category labels that had new articles.

    Returns:
        Formatted digest text.
    """
    if not articles:
        return ""

    category_str = ", ".join(sorted(set(categories_with_new)))
    header = (
        "━━━ Emerging Tech Digest ━━━\n"
        f"Sourced from {feeds_scanned} feeds across {len(CATEGORY_MAP)} categories:\n"
        f"New articles in: {category_str}"
    )

    body_parts: list[str] = []
    for article in articles:
        body_parts.append(_format_article_block(article))

    footer = "━━━━━━━━━━━━━━━━━━━"

    return f"{header}\n\n📰 Intelligence Brief\n\n{''.join(body_parts)}{footer}\n"
