"""Tests for src/digest_assembler.py."""
from src.digest_assembler import assemble_digest
from src.types import Article


def _article(
    title: str,
    bullets: str = "",
    briefing: str = "",
    feed_label: str = "Test Feed",
    url: str = "https://example.com/article",
    url_hash: str = "hash1",
) -> Article:
    return Article(
        title=title,
        url=url,
        summary=f"Summary of {title}",
        guid=f"guid-{title}",
        feed_key="test",
        feed_label=feed_label,
        category="AI & Digital Transformation",
        url_hash=url_hash,
        bullets=bullets,
        director_briefing=briefing,
    )


class TestAssembleDigest:
    def test_empty_articles_returns_empty_string(self):
        result = assemble_digest([], feeds_scanned=10, categories_with_new=[])
        assert result == ""

    def test_single_article_no_bullets(self):
        article = _article("Test Article")
        result = assemble_digest(
            [article],
            feeds_scanned=10,
            categories_with_new=["AI & Digital Transformation"],
        )
        assert "━━━ Emerging Tech Digest ━━━" in result
        assert "[Test Article]" in result
        assert "Source: Test Feed" in result
        assert "https://example.com/article" in result
        assert "📰 Intelligence Brief" in result
        assert "━━━━━━━━━━━━━━━━━━━" in result

    def test_article_with_date_shown(self):
        article = _article("With Date", url_hash="h1")
        article.date = "2024-06-13"
        result = assemble_digest(
            [article],
            feeds_scanned=10,
            categories_with_new=["AI & Digital Transformation"],
        )
        assert "2024-06-13" in result
        assert " | 2024-06-13" in result

    def test_article_without_date_no_trailing_pipe(self):
        """When date is empty, no trailing ' | YYYY-MM-DD' should appear."""
        article = _article("No Date", url_hash="h2")
        article.date = ""
        result = assemble_digest(
            [article],
            feeds_scanned=10,
            categories_with_new=["AI & Digital Transformation"],
        )
        line = [l for l in result.split("\n") if "Source: Test Feed" in l][0]
        # Still has " | " between Source and Link, but no date suffix
        assert " | " in line
        assert "Source: Test Feed | Link:" in line
        # No trailing date
        assert not line.endswith(" | ") and " | 20" not in line

    def test_article_with_bullets_and_briefing(self):
        article = _article(
            "Nvidia B200",
            bullets="- Nvidia launched B200 with 2.5x performance\n- $30K per unit pricing",
            briefing="- **Executive Synthesis:** Game-changing AI hardware",
        )
        result = assemble_digest(
            [article],
            feeds_scanned=10,
            categories_with_new=["AI & Digital Transformation"],
        )
        assert "- Nvidia launched B200" in result
        assert "Executive Synthesis" in result
        assert "2.5x performance" in result

    def test_multiple_articles(self):
        articles = [
            _article("Article One", bullets="- Bullet one"),
            _article("Article Two", bullets="- Bullet two"),
        ]
        result = assemble_digest(
            articles,
            feeds_scanned=10,
            categories_with_new=["AI & Digital Transformation"],
        )
        assert "[Article One]" in result
        assert "[Article Two]" in result
        assert "- Bullet one" in result
        assert "- Bullet two" in result

    def test_feeds_scanned_in_header(self):
        article = _article("Test")
        result = assemble_digest(
            [article],
            feeds_scanned=8,
            categories_with_new=["AI & Digital Transformation"],
        )
        assert "Sourced from 8 feeds" in result

    def test_categories_in_header(self):
        article = _article("Test")
        result = assemble_digest(
            [article],
            feeds_scanned=10,
            categories_with_new=["AI & Digital Transformation", "Fin-Tech"],
        )
        assert "AI & Digital Transformation" in result
        assert "Fin-Tech" in result
