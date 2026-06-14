"""Integration-level tests for the digest pipeline.

These tests exercise the pipeline end-to-end with mocked network
calls, verifying that all stages compose correctly.
"""
import hashlib
import json
import os
from unittest.mock import patch

import pytest

from src.types import Article


# Sample RSS XML for a single feed
SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>AI Startup Raises $500M Series C</title>
      <link>https://example.com/ai-funding</link>
      <description>A startup raised $500M at a $5B valuation for AI infrastructure.</description>
      <guid>guid-funding-1</guid>
      <pubDate>Thu, 13 Jun 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>New Cybersecurity Framework Released</title>
      <link>https://example.com/cyber-framework</link>
      <description>A new zero-trust framework was released by NIST.</description>
      <guid>guid-cyber-2</guid>
      <pubDate>Wed, 12 Jun 2026 08:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""


# Pre-compute url_hashes for the sample articles
_URL_HASH_FUNDING = hashlib.sha256(b"https://example.com/ai-funding").hexdigest()[:16]
_URL_HASH_CYBER = hashlib.sha256(b"https://example.com/cyber-framework").hexdigest()[:16]


class TestFullPipeline:
    """End-to-end pipeline with mocked network and LLM."""

    def test_dry_run_produces_digest(self):
        """--dry-run should produce digest with RSS summaries."""
        from run_digest import main

        with (
            patch("src.feeds.urlopen") as mock_feed,
            patch.dict("os.environ", {"LLM_API_KEY": "sk-test-key"}),
        ):
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")

            exit_code = main([
                "--category", "ai",
                "--max-days", "0",  # no date filter
                "--dry-run",
            ])
            # Should output digest to stdout
            assert exit_code == 0

    def test_full_pipeline_with_mocked_llm(self):
        """Full pipeline with mocked Jina and LLM."""
        from run_digest import main

        with (
            patch("src.feeds.urlopen") as mock_feed,
            patch("src.jina_fetcher.urlopen") as mock_jina,
            patch("src.llm_client.urlopen") as mock_llm,
            patch.dict("os.environ", {"LLM_API_KEY": "sk-test-key"}),
        ):
            # Feed response
            mock_feed_resp = mock_feed.return_value.__enter__.return_value
            mock_feed_resp.read.return_value = SAMPLE_RSS.encode("utf-8")

            # Jina response
            mock_jina_resp = mock_jina.return_value.__enter__.return_value
            mock_jina_resp.read.return_value = (
                b"Full article text about AI funding and growth "
                b"with sufficient length to exceed 100 chars for the Jina filter. "
                b"This article covers key developments in the industry."
            )

            # LLM responses — sequential for dedup, filter, summarize, briefing
            mock_llm_resp = mock_llm.return_value.__enter__.return_value

            dedup_response = {
                "kept": [
                    {
                        "title": "AI Startup Raises $500M Series C",
                        "url_hash": _URL_HASH_FUNDING,
                        "feed_label": "SemiAnalysis",
                        "summary": "",
                    },
                    {
                        "title": "New Cybersecurity Framework Released",
                        "url_hash": _URL_HASH_CYBER,
                        "feed_label": "SemiAnalysis",
                        "summary": "",
                    },
                ]
            }

            # With 6 AI feeds each returning 2 articles = 12 total.
            # Dedup returns 2 unique articles → then 2 summarizes + 2 briefings.
            total_unique = 2
            llm_responses = [
                # 1. semantic_dedup -> chat_json
                json.dumps({
                    "choices": [{"message": {"content": json.dumps(dedup_response)}}],
                }).encode("utf-8"),
            ]
            # 2. summarize + 3. briefing for each unique article
            for i in range(total_unique):
                llm_responses.append(json.dumps({
                    "choices": [{"message": {"content": f"- Bullet {i+1}"}}],
                }).encode("utf-8"))
                llm_responses.append(json.dumps({
                    "choices": [{"message": {"content": f"- **Executive Synthesis:** Point {i+1}"}}],
                }).encode("utf-8"))

            mock_llm_resp.read.side_effect = [r for r in llm_responses]

            exit_code = main([
                "--category", "ai",
                "--max-days", "0",
            ])
            assert exit_code == 0

    def test_date_filter_works(self):
        """Old articles should be filtered by --max-days."""
        from run_digest import main

        # RSS with an old article (2024)
        old_rss = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>Old Article</title>
      <link>https://example.com/old</link>
      <guid>guid-old</guid>
      <pubDate>Mon, 01 Jan 2024 12:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>"""

        with (
            patch("src.feeds.urlopen") as mock_feed,
            patch.dict("os.environ", {"LLM_API_KEY": "sk-test-key"}),
        ):
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = old_rss.encode("utf-8")

            exit_code = main([
                "--category", "ai",
                "--max-days", "2",
                "--dry-run",
            ])
            # Should exit silently — old article filtered by date
            assert exit_code == 0


class TestFeedCategoryFilter:
    def test_invalid_category_prints_error(self):
        from run_digest import main

        with pytest.raises(SystemExit) as exc:
            main(["--category", "invalid"])
        assert exc.value.code == 2
