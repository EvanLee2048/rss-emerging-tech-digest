"""Tests for src/feeds.py date parsing."""
import xml.etree.ElementTree as ET

import pytest

from src.feeds import _parse_date, _parse_rss_items
from src.types import FeedConfig


class TestParseDate:
    def test_rfc2822_date(self):
        """Mon, 01 Jan 2024 12:00:00 +0000"""
        assert _parse_date("Mon, 01 Jan 2024 12:00:00 +0000") == "2024-01-01"

    def test_rfc2822_with_gmt(self):
        """Mon, 01 Jan 2024 12:00:00 GMT"""
        assert _parse_date("Mon, 01 Jan 2024 12:00:00 GMT") == "2024-01-01"

    def test_iso8601_with_tz(self):
        """2024-06-13T14:30:00+00:00"""
        assert _parse_date("2024-06-13T14:30:00+00:00") == "2024-06-13"

    def test_iso8601_zulu(self):
        """2024-06-13T14:30:00Z"""
        assert _parse_date("2024-06-13T14:30:00Z") == "2024-06-13"

    def test_iso8601_no_tz(self):
        """2024-01-01 12:00:00"""
        assert _parse_date("2024-01-01 12:00:00") == "2024-01-01"

    def test_empty_string(self):
        assert _parse_date("") == ""

    def test_none(self):
        assert _parse_date(None) == ""

    def test_invalid_date(self):
        """Non-date string returns empty."""
        assert _parse_date("not a date") == ""

    def test_date_in_text_fallback(self):
        """Extract YYYY-MM-DD substring as last resort."""
        assert _parse_date("Published 2024-03-15 in the Journal") == "2024-03-15"


class TestParseRssWithDates:
    RSS_WITH_DATES = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Date Test Feed</title>
    <item>
      <title>Article With Date</title>
      <link>https://example.com/dated</link>
      <description>Description</description>
      <guid>guid-date</guid>
      <pubDate>Wed, 12 Jun 2024 08:30:00 +0000</pubDate>
    </item>
    <item>
      <title>Article Without Date</title>
      <link>https://example.com/no-date</link>
      <description>No date here</description>
      <guid>guid-no-date</guid>
    </item>
  </channel>
</rss>"""

    ATOM_WITH_DATES = """<?xml version="1.0"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Date Test</title>
  <entry>
    <title>Atom With Published</title>
    <link href="https://example.com/atom-pub"/>
    <summary>Atom published</summary>
    <id>atom-pub-guid</id>
    <published>2024-06-13T10:00:00Z</published>
  </entry>
  <entry>
    <title>Atom With Updated</title>
    <link href="https://example.com/atom-upd"/>
    <summary>Atom updated</summary>
    <id>atom-upd-guid</id>
    <updated>2024-06-12T18:00:00+00:00</updated>
  </entry>
</feed>"""

    @staticmethod
    def _cfg() -> FeedConfig:
        return FeedConfig("test", "Test Feed", "http://example.com/rss", "ai")

    def test_rss_with_pubdate(self):
        root = ET.fromstring(self.RSS_WITH_DATES)
        articles = _parse_rss_items(root, self._cfg())
        assert len(articles) == 2
        assert articles[0].date == "2024-06-12"
        assert articles[1].date == ""  # No pubDate

    def test_atom_with_published(self):
        root = ET.fromstring(self.ATOM_WITH_DATES)
        articles = _parse_rss_items(root, self._cfg())
        assert len(articles) == 2
        assert articles[0].date == "2024-06-13"
        assert articles[1].date == "2024-06-12"
