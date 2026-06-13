"""URL-level dedup state management.

Records article URL hashes seen in previous runs so subsequent runs only
emit new articles. First run establishes a baseline (records all URLs,
emits nothing).

State is persisted as JSON files in a configurable directory.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

from src.types import Article


class WatermarkStore:
    """Per-feed watermark tracking for URL-level dedup."""

    def __init__(self, state_dir: str, max_seen: int = 500) -> None:
        self._state_dir = Path(state_dir)
        self._max_seen = max_seen
        self._data: dict[str, dict] = {}
        self._dirty_feeds: set[str] = set()

    # ── load / save ──────────────────────────────────────────────────

    def load(self) -> None:
        """Load all persisted watermark data from the state directory."""
        self._state_dir.mkdir(parents=True, exist_ok=True)
        for fpath in self._state_dir.glob("*.json"):
            feed_name = fpath.stem
            try:
                self._data[feed_name] = json.loads(fpath.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self._data[feed_name] = {"seen_hashes": [], "first_run": True}
        self._dirty_feeds.clear()

    def save(self, feed_name: Optional[str] = None) -> None:
        """Persist dirty watermark data to disk.

        Args:
            feed_name: If given, save only that feed. Otherwise save all dirty feeds.
        """
        self._state_dir.mkdir(parents=True, exist_ok=True)
        targets = [feed_name] if feed_name else list(self._dirty_feeds)
        for name in targets:
            if name not in self._data:
                continue
            fpath = self._state_dir / f"{name}.json"
            tmp = fpath.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._data[name], indent=2, sort_keys=True),
                encoding="utf-8",
            )
            os.replace(tmp, fpath)
            self._dirty_feeds.discard(name)

    def save_all(self) -> None:
        """Persist all dirty feeds."""
        self.save()

    # ── per-feed access ──────────────────────────────────────────────

    def _ensure(self, feed_name: str) -> dict:
        if feed_name not in self._data:
            self._data[feed_name] = {"seen_hashes": [], "first_run": True}
        return self._data[feed_name]

    def is_first_run(self, feed_name: str) -> bool:
        return bool(self._ensure(feed_name).get("first_run", True))

    def seen_hashes(self, feed_name: str) -> set[str]:
        return set(self._ensure(feed_name).get("seen_hashes", []))

    # ── dedup ────────────────────────────────────────────────────────

    @staticmethod
    def _url_hash(url: str) -> str:
        return hashlib.sha256(url.encode()).hexdigest()[:16]

    def filter_new_articles(
        self, articles: list[Article]
    ) -> list[Article]:
        """Filter articles, returning only those with unseen URLs.

        Side effect: records ALL article URLs in the watermark so save()
        persists them. On first run for a feed, records but returns empty.
        """
        new_articles: list[Article] = []
        # Batch first-run check: group articles by feed, capture first_run
        # state once per feed before processing any articles.
        feed_first_run: dict[str, bool] = {}
        for article in articles:
            if article.feed_key not in feed_first_run:
                fd = self._ensure(article.feed_key)
                feed_first_run[article.feed_key] = fd.get("first_run", True)

        for article in articles:
            feed_data = self._ensure(article.feed_key)
            seen = set(feed_data.get("seen_hashes", []))
            url_hash = self._url_hash(article.url)
            article.url_hash = url_hash

            if url_hash in seen:
                continue

            was_first_run = feed_first_run.get(article.feed_key, True)

            # Record this hash
            seen_updated: list[str] = list(seen)
            seen_updated.append(url_hash)
            if len(seen_updated) > self._max_seen:
                seen_updated = seen_updated[-self._max_seen:]
            feed_data["seen_hashes"] = seen_updated
            feed_data["first_run"] = False
            self._dirty_feeds.add(article.feed_key)

            if not was_first_run:
                new_articles.append(article)

        return new_articles
