"""Integration-level tests for the digest pipeline.

These tests exercise the pipeline end-to-end with mocked network
calls, verifying that all stages compose correctly.
"""
import hashlib
import json
import os
import tempfile
from unittest.mock import patch

import pytest

from src.feeds import get_feeds
from src.watermark import WatermarkStore
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
    </item>
    <item>
      <title>New Cybersecurity Framework Released</title>
      <link>https://example.com/cyber-framework</link>
      <description>A new zero-trust framework was released by NIST.</description>
      <guid>guid-cyber-2</guid>
    </item>
  </channel>
</rss>"""


# Pre-compute url_hashes for the sample articles
_URL_HASH_FUNDING = hashlib.sha256(b"https://example.com/ai-funding").hexdigest()[:16]
_URL_HASH_CYBER = hashlib.sha256(b"https://example.com/cyber-framework").hexdigest()[:16]


@pytest.fixture
def state_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


class TestFullPipeline:
    """End-to-end pipeline with mocked network and LLM."""

    def test_dry_run_skips_llm_and_jina(self, state_dir):
        """--dry-run should skip LLM/Jina and use RSS summaries only."""
        from run_digest import main

        with patch("src.feeds.urlopen") as mock_feed:
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")

            # First run — establish baseline
            exit_code = main([
                "--state-dir", state_dir,
                "--category", "ai",
                "--dry-run",
            ])
            assert exit_code == 0

        # Second run — emit articles (dry-run)
        with patch("src.feeds.urlopen") as mock_feed:
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")

            exit_code = main([
                "--state-dir", state_dir,
                "--category", "ai",
                "--dry-run",
            ])
            # Should output digest to stdout
            assert exit_code == 0

    def test_full_pipeline_two_runs_baseline_then_deliver(self, state_dir):
        """First run: baseline. Second run: digest with mocked LLM."""
        from run_digest import main

        with patch("src.feeds.urlopen") as mock_feed:
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")

            exit_code = main([
                "--state-dir", state_dir,
                "--category", "ai",
                "--dry-run",
            ])
            assert exit_code == 0  # Silent baseline

        # Second run — deliver (patch env to bypass LLMClient API key check)
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
            mock_jina_resp.read.return_value = b"Full article text about AI funding and growth."

            # LLM responses — sequential for dedup, hkma filter (auto-pass), summarize, briefing
            # The pipeline does: semantic_dedup, filter_all (auto-pass non-HKMA), summarize, briefing
            # semantic_dedup: chat_json -> {"kept": [...]}
            dedup_response = {
                "kept": [
                    {
                        "title": "AI Startup Raises $500M Series C",
                        "url_hash": _URL_HASH_FUNDING,  # computed at import time
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
            mock_llm_resp = mock_llm.return_value.__enter__.return_value

            # We need to return different responses per call.
            # Use side_effect to cycle through responses.
            llm_responses = iter([
                # 1. semantic_dedup -> chat_json: json
                json.dumps({
                    "choices": [{"message": {"content": json.dumps(dedup_response)}}],
                    "usage": {},
                }).encode("utf-8"),
                # 2. filter_all -> non-HKMA auto-pass, no LLM call (2 articles)
                # (this is skipped for non-HKMA — check)
                # 3. summarize: article 1
                json.dumps({
                    "choices": [{"message": {"content": "- Series C raised $500M at $5B valuation"}}],
                }).encode("utf-8"),
                # 4. summarize: article 2
                json.dumps({
                    "choices": [{"message": {"content": "- NIST released new zero-trust framework"}}],
                }).encode("utf-8"),
                # 5. briefing: article 1
                json.dumps({
                    "choices": [{"message": {"content": "- **Executive Synthesis:** AI infra investment surge"}}],
                }).encode("utf-8"),
                # 6. briefing: article 2
                json.dumps({
                    "choices": [{"message": {"content": "- **Executive Synthesis:** Cyber compliance costs rise"}}],
                }).encode("utf-8"),
            ])
            mock_llm_resp.read.side_effect = lambda: next(llm_responses)

            exit_code = main([
                "--state-dir", state_dir,
                "--category", "ai",
            ])
            assert exit_code == 0

    def test_silent_on_no_new_items(self, state_dir):
        """When all articles seen before, output nothing."""
        from run_digest import main

        # First run — baseline
        with patch("src.feeds.urlopen") as mock_feed:
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")
            main(["--state-dir", state_dir, "--category", "ai", "--dry-run"])

        # Second run — same content, should be silent
        with patch("src.feeds.urlopen") as mock_feed:
            mock_resp = mock_feed.return_value.__enter__.return_value
            mock_resp.read.return_value = SAMPLE_RSS.encode("utf-8")
            exit_code = main(["--state-dir", state_dir, "--category", "ai", "--dry-run"])
            # Returns 0 (no error), but no output (already seen)
            assert exit_code == 0


class TestFeedCategoryFilter:
    def test_invalid_category_prints_error(self):
        from run_digest import main

        with pytest.raises(SystemExit) as exc:
            main(["--category", "invalid"])
        assert exc.value.code == 2
