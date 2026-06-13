"""Tests for src/types.py."""
import pytest
from src.types import Article, FeedConfig, ALL_FEEDS, CATEGORY_MAP


class TestFeedConfig:
    def test_all_feeds_loaded(self):
        assert len(ALL_FEEDS) == 10

    def test_all_categories_represented(self):
        cats = {f.category for f in ALL_FEEDS}
        assert cats == set(CATEGORY_MAP.keys())

    def test_category_weights(self):
        """Verify counts match the skill spec: 6 AI, 1 each for others."""
        from collections import Counter
        counts = Counter(f.category for f in ALL_FEEDS)
        assert counts["ai"] == 6
        assert counts["cyber"] == 1
        assert counts["fintech"] == 1
        assert counts["web3"] == 1
        assert counts["hkma"] == 1


class TestArticle:
    def test_default_values(self):
        a = Article(
            title="Test",
            url="https://example.com/article",
            summary="Some summary",
            guid="guid-1",
            feed_key="testfeed",
            feed_label="Test Feed",
            category="AI & Digital Transformation",
        )
        assert a.url_hash == ""
        assert a.full_text == ""
        assert a.is_hkma is False
        assert a.filter_passed is True
        assert a.bullets == ""
        assert a.director_briefing == ""
