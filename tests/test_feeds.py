"""Tests for src/feeds.py."""
import xml.etree.ElementTree as ET
from unittest.mock import patch

import pytest

from src.feeds import fetch_feed, get_feeds, _parse_rss_items
from src.types import FeedConfig, Article


class TestGetFeeds:
    def test_all_feeds(self):
        feeds = get_feeds("all")
        assert len(feeds) == 10

    def test_category_filter(self):
        feeds = get_feeds("ai")
        assert all(f.category == "ai" for f in feeds)
        assert len(feeds) == 6

        feeds = get_feeds("hkma")
        assert len(feeds) == 1
        assert feeds[0].watcher_name == "hkma"

    def test_none_returns_all(self):
        feeds = get_feeds(None)
        assert len(feeds) == 10


class TestParseRssItems:
    RSS_XML = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article One</title>
      <link>https://example.com/1</link>
      <description>Description one</description>
      <guid>guid-1</guid>
    </item>
    <item>
      <title>Article Two</title>
      <link>https://example.com/2</link>
      <description>Description two</description>
    </item>
  </channel>
</rss>"""

    ATOM_XML = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <title>Atom Article</title>
    <link href="https://example.com/atom1"/>
    <summary>Atom summary</summary>
    <id>atom-guid-1</id>
  </entry>
</feed>"""

    @staticmethod
    def _cfg() -> FeedConfig:
        return FeedConfig("test", "Test Feed", "http://example.com/rss", "ai")

    def test_parse_rss(self):
        root = ET.fromstring(self.RSS_XML)
        articles = _parse_rss_items(root, self._cfg())
        assert len(articles) == 2
        assert articles[0].title == "Article One"
        assert articles[0].url == "https://example.com/1"
        assert articles[0].summary == "Description one"
        assert articles[0].guid == "guid-1"
        assert articles[0].feed_key == "test"

    def test_parse_atom(self):
        root = ET.fromstring(self.ATOM_XML)
        articles = _parse_rss_items(root, self._cfg())
        assert len(articles) == 1
        assert articles[0].title == "Atom Article"
        assert articles[0].url == "https://example.com/atom1"
        assert articles[0].summary == "Atom summary"
        assert articles[0].guid == "atom-guid-1"

    def test_no_guid_falls_back_to_url(self):
        xml = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item>
      <title>No GUID</title>
      <link>https://example.com/no-guid</link>
    </item>
  </channel>
</rss>"""
        root = ET.fromstring(xml)
        articles = _parse_rss_items(root, self._cfg())
        assert len(articles) == 1
        assert articles[0].guid == "https://example.com/no-guid"

    def test_empty_items_filtered(self):
        xml = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <item><title>Only Title</title></item>
    <item><link>https://example.com/has-link</link><title>Has Link</title></item>
  </channel>
</rss>"""
        root = ET.fromstring(xml)
        articles = _parse_rss_items(root, self._cfg())
        # feed.fetch_feed filters out articles with no URL
        from src.feeds import fetch_feed
        with patch("src.feeds.urlopen") as mock_urlopen:
            mock_resp = mock_urlopen.return_value.__enter__.return_value
            mock_resp.read.return_value = xml.encode("utf-8")
            result = fetch_feed(self._cfg())
            assert result is not None
            # Has Link should be included, Only Title should be filtered (no url)
            assert len([a for a in result if a.url]) == 1
            assert [a for a in result if a.url][0].url == "https://example.com/has-link"


class TestFetchFeed:
    def test_returns_none_on_network_error(self):
        with patch("src.feeds.urlopen") as mock:
            mock.side_effect = OSError("Connection refused")
            result = fetch_feed(
                FeedConfig("test", "Test", "http://example.com/rss", "ai")
            )
            assert result is None

    def test_returns_none_on_bad_xml(self):
        with patch("src.feeds.urlopen") as mock:
            mock_resp = mock.return_value.__enter__.return_value
            mock_resp.read.return_value = b"not xml"
            result = fetch_feed(
                FeedConfig("test", "Test", "http://example.com/rss", "ai")
            )
            assert result is None
