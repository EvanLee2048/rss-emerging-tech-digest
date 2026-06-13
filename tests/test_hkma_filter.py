"""Tests for src/hkma_filter.py."""
from unittest.mock import MagicMock

import pytest

from src.hkma_filter import filter_article, filter_all, is_hkma_item
from src.types import Article


def _article(
    feed_key: str = "testfeed",
    title: str = "Test Article",
    full_text: str = "",
    summary: str = "RSS summary",
) -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        summary=summary,
        guid="guid-1",
        feed_key=feed_key,
        feed_label="Test Feed",
        category="Test",
        full_text=full_text,
    )


class TestIsHkmaItem:
    def test_hkma_feed(self):
        article = _article(feed_key="hkma")
        assert is_hkma_item(article) is True

    def test_non_hkma_feed(self):
        article = _article(feed_key="semianalysis")
        assert is_hkma_item(article) is False


class TestFilterArticle:
    def test_non_hkma_auto_passed(self):
        """Non-HKMA articles pass without LLM cost."""
        article = _article(feed_key="semianalysis")
        mock_llm = MagicMock()
        result = filter_article(article, mock_llm)
        assert result.filter_passed is True
        assert result.filter_reason == "Non-HKMA - auto-passed"
        mock_llm.chat_json.assert_not_called()

    def test_hkma_kept(self):
        article = _article(
            feed_key="hkma",
            title="HKMA issues new fintech guidelines",
            full_text="The HKMA today issued new regulatory guidelines for digital banking operations and AI governance.",
        )
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "passed": True,
            "reason": "Fintech policy change - keep",
        }
        result = filter_article(article, mock_llm)
        assert result.filter_passed is True
        assert result.is_hkma is True

    def test_hkma_filtered_out(self):
        article = _article(
            feed_key="hkma",
            title="Scam alert: phishing emails",
            full_text="The HKMA warns the public about fraudulent emails claiming to be from a local bank.",
        )
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "passed": False,
            "reason": "Individual scam alert - filter out",
        }
        result = filter_article(article, mock_llm)
        assert result.filter_passed is False

    def test_hkma_no_content(self):
        article = _article(
            feed_key="hkma",
            title="HKMA statement",
            summary="",
        )
        mock_llm = MagicMock()
        result = filter_article(article, mock_llm)
        assert result.filter_passed is False
        assert "No content" in result.filter_reason

    def test_llm_error_defaults_to_keep(self):
        """On LLM error, keep the article by default."""
        article = _article(
            feed_key="hkma",
            title="HKMA announcement",
            full_text="Some content here",
        )
        mock_llm = MagicMock()
        mock_llm.chat_json.side_effect = RuntimeError("API down")
        result = filter_article(article, mock_llm)
        assert result.filter_passed is True
        assert "failed" in result.filter_reason


class TestFilterAll:
    def test_mixed_feeds(self):
        articles = [
            _article(feed_key="semianalysis", title="AI Article"),
            _article(
                feed_key="hkma",
                title="Regulatory update",
                full_text="HKMA fintech guidelines",
            ),
            _article(
                feed_key="hkma",
                title="Scam alert",
                full_text="Phishing warning to consumers",
            ),
        ]

        mock_llm = MagicMock()
        # Non-HKMA auto-passed, HKMA fintech kept, HKMA scam filtered
        def side_effect(*args, **kwargs):
            user = kwargs.get("user_prompt", "")
            if "Phishing" in user or "Scam" in user:
                return {"passed": False, "reason": "Scam alert"}
            return {"passed": True, "reason": "Keep"}

        mock_llm.chat_json.side_effect = side_effect

        result = filter_all(articles, mock_llm)
        assert len(result) == 2  # AI + HKMA fintech, HKMA scam filtered
        titles = [a.title for a in result]
        assert "AI Article" in titles
        assert "Regulatory update" in titles
        assert "Scam alert" not in titles
