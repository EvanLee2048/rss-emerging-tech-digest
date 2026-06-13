"""Tests for src/jina_fetcher.py."""
from unittest.mock import patch

import pytest

from src.jina_fetcher import fetch_full_text, enrich_article
from src.types import Article


def _article(url: str = "https://example.com/article") -> Article:
    return Article(
        title="Test",
        url=url,
        summary="RSS summary fallback",
        guid="guid-1",
        feed_key="test",
        feed_label="Test Feed",
        category="Test",
    )


class TestFetchFullText:
    def test_returns_full_text_on_success(self):
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = b"Full article text from Jina with details about AI trends and market movements. The article covers multiple key developments in the AI industry including large language models, enterprise AI adoption, and regulatory frameworks being developed across different jurisdictions. This content exceeds 100 characters easily."
            result = fetch_full_text(article)
            assert "Full article text" in result
            assert "RSS summary" not in result

    def test_fallback_on_jina_warning(self):
        """Jina returns 'Warning: ...' for blocked pages."""
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = b"Warning: Target URL returned error 403"
            result = fetch_full_text(article)
            assert result == "RSS summary fallback"

    def test_fallback_on_short_response(self):
        """Very short response (<100 chars) treated as error."""
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = b"short"
            result = fetch_full_text(article)
            assert result == "RSS summary fallback"

    def test_fallback_on_network_error(self):
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock.side_effect = OSError("Timeout")
            result = fetch_full_text(article)
            assert result == "RSS summary fallback"

    def test_empty_url_returns_summary(self):
        article = _article(url="")
        result = fetch_full_text(article)
        assert result == "RSS summary fallback"

    def test_article_enriched(self):
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = b"Full enriched text content about the latest AI industry developments including new model releases and funding rounds. This article provides comprehensive coverage of the technology landscape that continues to evolve rapidly across multiple sectors."
            enriched = enrich_article(article)
            assert enriched.full_text.startswith("Full enriched text content")
            assert enriched.title == "Test"
