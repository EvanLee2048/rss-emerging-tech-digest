"""Tests for src/summarizer.py."""
from unittest.mock import MagicMock

import pytest

from src.summarizer import summarize_article
from src.types import Article


def _article(full_text: str = "", summary: str = "") -> Article:
    summ = summary if summary else "RSS summary"
    return Article(
        title="Test Article",
        url="https://example.com/test",
        summary=summ,
        guid="guid-1",
        feed_key="test",
        feed_label="Test Feed",
        category="Test",
        full_text=full_text,
    )


class TestSummarizeArticle:
    def test_returns_bullets_on_success(self):
        article = _article(full_text="Long article text about AI trends and market movements.")
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "- AI market grew 45% in Q3\n- Nvidia leads with 78% market share"
        result = summarize_article(article, mock_llm)
        assert "45%" in result
        assert "Nvidia" in result
        assert result.startswith("- ")

    def test_fallback_on_no_content(self):
        # Build article directly with no content at all
        article = Article(
            title="Test",
            url="",
            summary="",
            guid="",
            feed_key="test",
            feed_label="Test",
            category="Test",
        )
        mock_llm = MagicMock()
        result = summarize_article(article, mock_llm)
        assert "No content" in result

    def test_fallback_on_llm_error(self):
        article = _article(full_text="Some content")
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = RuntimeError("API error")
        result = summarize_article(article, mock_llm)
        assert "failed" in result

    def test_uses_full_text_over_summary(self):
        article = _article(
            full_text="Full article body with detailed analysis",
            summary="RSS summary snippet",
        )
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "- Brief bullet point"
        summarize_article(article, mock_llm)
        # Verify full_text was sent, not summary
        call_args = mock_llm.chat.call_args
        user_prompt = call_args[1]["user_prompt"]
        assert "Full article body" in user_prompt
        assert "RSS summary snippet" not in user_prompt
