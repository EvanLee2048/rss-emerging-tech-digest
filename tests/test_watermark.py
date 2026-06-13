"""Tests for src/watermark.py."""
import json
import tempfile
from pathlib import Path

import pytest

from src.types import Article
from src.watermark import WatermarkStore


@pytest.fixture
def state_dir():
    with tempfile.TemporaryDirectory() as td:
        yield td


def _make_article(url: str, feed_key: str = "testfeed") -> Article:
    return Article(
        title=f"Article {url}",
        url=url,
        summary="summary",
        guid=url,
        feed_key=feed_key,
        feed_label="Test Feed",
        category="Test",
    )


class TestWatermarkStore:
    def test_first_run_returns_nothing(self, state_dir):
        """First run establishes baseline — no articles emitted."""
        wm = WatermarkStore(state_dir)
        wm.load()
        articles = [_make_article("https://example.com/a")]
        new = wm.filter_new_articles(articles)
        assert new == []
        # But watermark should be written
        wm.save()
        state_path = Path(state_dir) / "testfeed.json"
        assert state_path.exists()
        data = json.loads(state_path.read_text())
        assert len(data["seen_hashes"]) == 1

    def test_second_run_returns_only_new(self, state_dir):
        wm = WatermarkStore(state_dir)
        wm.load()
        # First run — establish baseline
        articles_a = [_make_article("https://example.com/a")]
        assert wm.filter_new_articles(articles_a) == []
        wm.save()

        # Second run — same article filtered, new article emitted
        wm2 = WatermarkStore(state_dir)
        wm2.load()
        articles_b = [
            _make_article("https://example.com/a"),
            _make_article("https://example.com/b"),
        ]
        new = wm2.filter_new_articles(articles_b)
        assert len(new) == 1
        assert new[0].url == "https://example.com/b"

    def test_duplicate_urls_in_same_batch(self, state_dir):
        """Same URL twice in one batch — only emitted once."""
        wm = WatermarkStore(state_dir)
        wm.load()
        # First run baseline
        articles = [_make_article("https://example.com/a"),
                     _make_article("https://example.com/a")]
        assert wm.filter_new_articles(articles) == []
        wm.save()

        # Second run — only one emitted
        wm2 = WatermarkStore(state_dir)
        wm2.load()
        new = wm2.filter_new_articles([_make_article("https://example.com/a")])
        assert new == []

    def test_multiple_feeds_independent(self, state_dir):
        """Watermarks for different feeds are independent."""
        wm = WatermarkStore(state_dir)
        wm.load()

        art_feed1 = _make_article("https://example.com/x", feed_key="feed1")
        art_feed2 = _make_article("https://example.com/y", feed_key="feed2")

        # First run baseline for both
        assert wm.filter_new_articles([art_feed1, art_feed2]) == []
        wm.save()

        # Second run — both should return nothing (hashes already seen)
        wm2 = WatermarkStore(state_dir)
        wm2.load()
        new = wm2.filter_new_articles([
            _make_article("https://example.com/x", feed_key="feed1"),
            _make_article("https://example.com/y", feed_key="feed2"),
        ])
        assert new == []

    def test_max_seen_bounded(self, state_dir):
        wm = WatermarkStore(state_dir, max_seen=3)
        wm.load()
        # First run — establish baseline with 3 articles
        arts = [_make_article(f"https://example.com/{i}") for i in range(3)]
        assert wm.filter_new_articles(arts) == []
        wm.save()

        # Add 3 more
        wm2 = WatermarkStore(state_dir, max_seen=3)
        wm2.load()
        arts2 = [_make_article(f"https://example.com/{i}") for i in range(3, 6)]
        new = wm2.filter_new_articles(arts2)
        assert len(new) == 3

        # Oldest hashes should be evicted; total seen should be ≤3
        data = json.loads((Path(state_dir) / "testfeed.json").read_text())
        assert len(data["seen_hashes"]) <= 3
