"""Tests for src/dedup.py."""
from unittest.mock import MagicMock, patch

import pytest

from src.dedup import semantic_dedup
from src.types import Article


def _article(title: str, url_hash: str = "hash1") -> Article:
    return Article(
        title=title,
        url=f"https://example.com/{title.lower().replace(' ', '-')}",
        summary=f"Summary of {title}",
        guid=f"guid-{title}",
        feed_key="testfeed",
        feed_label="Test Feed",
        category="AI & Digital Transformation",
        url_hash=url_hash,
    )


class TestSemanticDedup:
    def test_single_article_passthrough(self):
        """Single article should pass through without LLM call."""
        articles = [_article("Article One")]
        result = semantic_dedup(articles, MagicMock())
        assert len(result) == 1

    def test_returns_deduped_list_on_llm_success(self):
        articles = [
            _article("Same Story A", url_hash="hash1"),
            _article("Same Story B", url_hash="hash2"),
        ]
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {
            "kept": [
                {
                    "title": "Same Story A",
                    "url_hash": "hash1",
                    "feed_label": "Test Feed",
                    "summary": "",
                }
            ]
        }

        result = semantic_dedup(articles, mock_llm)
        assert len(result) == 1
        assert result[0].url_hash == "hash1"

    def test_fallback_on_llm_error(self):
        """On LLM failure, keep all articles."""
        articles = [
            _article("Article A", url_hash="hash1"),
            _article("Article B", url_hash="hash2"),
        ]
        mock_llm = MagicMock()
        mock_llm.chat_json.side_effect = RuntimeError("API down")

        result = semantic_dedup(articles, mock_llm)
        assert len(result) == 2

    def test_fallback_on_empty_result(self):
        """If LLM returns empty kept list, keep all articles."""
        articles = [
            _article("Article A", url_hash="hash1"),
        ]
        mock_llm = MagicMock()
        mock_llm.chat_json.return_value = {"kept": []}

        result = semantic_dedup(articles, mock_llm)
        assert len(result) == 1
