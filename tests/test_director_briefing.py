"""Tests for src/director_briefing.py."""
from unittest.mock import MagicMock

import pytest

from src.director_briefing import generate_briefing
from src.types import Article


def _article(full_text: str = "", summary: str = "") -> Article:
    summ = summary if summary else "Nvidia announced a new AI training chip."
    return Article(
        title="Nvidia launches new AI chip",
        url="https://example.com/nvidia",
        summary=summ,
        guid="guid-1",
        feed_key="test",
        feed_label="Test Feed",
        category="AI & Digital Transformation",
        full_text=full_text,
    )


class TestGenerateBriefing:
    def test_returns_briefing_on_success(self):
        article = _article(full_text="Nvidia announced the B200 GPU with 2.5x performance improvement over H100.")
        mock_llm = MagicMock()
        mock_llm.chat.return_value = (
            "- **Executive Synthesis:** Nvidia's B200 redefines AI training economics.\n"
            "- **Corporate Strategy (Strategist):** Locks enterprise AI infrastructure dependency.\n"
            "- **Commercial Angle (Sales):** $30B+ TAM for next-gen AI inference hardware."
        )
        result = generate_briefing(article, mock_llm)
        assert "Executive Synthesis" in result
        assert "Corporate Strategy" in result
        assert "Commercial Angle" in result

    def test_fallback_on_no_content(self):
        # Build article directly with no content at all
        article = Article(
            title="Nvidia launches new AI chip",
            url="",
            summary="",
            guid="",
            feed_key="test",
            feed_label="Test",
            category="Test",
        )
        mock_llm = MagicMock()
        result = generate_briefing(article, mock_llm)
        assert "No content available" in result

    def test_fallback_on_llm_error(self):
        article = _article(full_text="Some content")
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = RuntimeError("API error")
        result = generate_briefing(article, mock_llm)
        assert "failed" in result

    def test_uses_full_text_when_available(self):
        article = _article(full_text="Detailed Nvidia B200 announcement body")
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "- Analysis"
        generate_briefing(article, mock_llm)
        call_args = mock_llm.chat.call_args
        user_prompt = call_args[1]["user_prompt"]
        assert "Detailed Nvidia" in user_prompt
