"""Tests for src/jina_fetcher.py."""
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

import pytest

from src.jina_fetcher import enrich_article, fetch_full_text
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


LONG_TEXT = (
    "Full article text with sufficient length to pass the 200-char threshold. "
    "This article covers multiple key developments in the AI industry including "
    "large language models, enterprise AI adoption, and regulatory frameworks "
    "being developed across different jurisdictions. This content is long enough."
)


class TestFetchFullText:
    # ── Direct fetch succeeds (Tier 1) ─────────────────────────────

    def test_direct_fetch_succeeds(self):
        """Direct fetch returns content → used immediately, no Jina call."""
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = LONG_TEXT.encode("utf-8")

            result = fetch_full_text(article)

            assert "Full article text" in result
            assert "RSS summary" not in result
            # urlopen called exactly once (first UA succeeds, no retry)
            assert mock.call_count == 1

    # ── Direct fails, Jina succeeds (Tier 1→2) ─────────────────────

    def test_direct_fails_jina_succeeds(self):
        """Direct fetch blocks (403) → Jina proxy used."""
        article = _article()

        # Jina success context manager + response
        jina_resp = MagicMock()
        jina_resp.read.return_value = b"Full article text from Jina proxy. " * 20
        jina_ctx = MagicMock()
        jina_ctx.__enter__.return_value = jina_resp

        with patch("src.jina_fetcher.urlopen") as mock:
            mock.side_effect = [
                HTTPError("", 403, "Forbidden", {}, None),
                HTTPError("", 403, "Forbidden", {}, None),
                jina_ctx,
            ]
            result = fetch_full_text(article)

        assert "Full article text from Jina proxy" in result
        assert "RSS summary" not in result

    def test_direct_short_jina_succeeds(self):
        """Direct returns short/blocked content → Jina fallback."""
        article = _article()
        direct_ctx = MagicMock()
        direct_resp = MagicMock()
        direct_resp.read.return_value = b"short"
        direct_ctx.__enter__.return_value = direct_resp

        jina_ctx = MagicMock()
        jina_resp = MagicMock()
        jina_resp.read.return_value = b"Full article text from Jina proxy. " * 20
        jina_ctx.__enter__.return_value = jina_resp

        with patch("src.jina_fetcher.urlopen") as mock:
            mock.side_effect = [direct_ctx, direct_ctx, jina_ctx]
            result = fetch_full_text(article)

        assert "Full article text from Jina proxy" in result

    # ── Both fail → RSS summary (Tier 3) ───────────────────────────

    def test_both_fail_returns_rss_summary(self):
        """Direct and Jina both fail → RSS summary fallback."""
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock.side_effect = OSError("Network error")
            result = fetch_full_text(article)
            assert result == "RSS summary fallback"

    def test_empty_url_returns_summary(self):
        article = _article(url="")
        result = fetch_full_text(article)
        assert result == "RSS summary fallback"

    # ── enrich_article ──────────────────────────────────────────────

    def test_article_enriched(self):
        article = _article()
        with patch("src.jina_fetcher.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = LONG_TEXT.encode("utf-8")
            enriched = enrich_article(article)
            assert enriched.full_text.startswith("Full article text")
            assert enriched.title == "Test"
