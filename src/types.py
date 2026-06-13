"""Shared data types for the RSS Emerging Tech Digest pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FeedConfig:
    """Configuration for a single RSS feed."""

    watcher_name: str
    label: str
    url: str
    category: str


@dataclass
class Article:
    """A single article fetched from an RSS feed, possibly enriched."""

    title: str
    url: str
    summary: str  # RSS-level description/summary
    guid: str
    feed_key: str
    feed_label: str
    category: str

    # Publication date (parsed from RSS pubDate or Atom published)
    date: str = ""

    # Enriched fields (set during pipeline processing)
    url_hash: str = ""
    full_text: str = ""  # Full article body from Jina
    is_hkma: bool = False
    filter_passed: bool = True
    filter_reason: str = ""

    # LLM-generated content
    bullets: str = ""  # Bullet-point summary
    director_briefing: str = ""  # Strategic Director Briefing


@dataclass
class DigestResult:
    """Result of a single pipeline run."""

    articles: list[Article] = field(default_factory=list)
    feeds_scanned: int = 0
    categories_with_new: list[str] = field(default_factory=list)
    updated_watermarks: dict[str, list[str]] = field(default_factory=dict)
    digest_text: str = ""
    error: Optional[str] = None


# Category definitions
CATEGORY_MAP: dict[str, str] = {
    "ai": "AI & Digital Transformation",
    "cyber": "Cyber Security & Tech Risk",
    "fintech": "Fin-Tech",
    "web3": "Web3",
    "hkma": "HK Tech Regulation",
}

ALL_FEEDS: list[FeedConfig] = [
    # ── AI & Digital Transformation ──
    FeedConfig("semianalysis", "SemiAnalysis", "https://www.semianalysis.com/feed", "ai"),
    FeedConfig("importai", "Import AI (Substack)", "https://importai.substack.com/feed", "ai"),
    FeedConfig("latentspace", "Latent Space", "https://www.latent.space/feed", "ai"),
    FeedConfig("venturebeat", "VentureBeat: Enterprise AI", "https://venturebeat.com/category/ai/feed/", "ai"),
    FeedConfig("gradientflow", "Gradient Flow", "https://gradientflow.com/feed/", "ai"),
    FeedConfig("infoq", "InfoQ: AI, ML and Data Engineering", "https://feed.infoq.com/ai-ml-data-eng/news", "ai"),
    # ── Cyber Security ──
    FeedConfig("darkreading", "Dark Reading", "https://www.darkreading.com/rss.xml", "cyber"),
    # ── Fin-Tech ──
    FeedConfig("paymentsdive", "Payments Dive", "https://www.paymentsdive.com/feeds/news/", "fintech"),
    # ── Web3 ──
    FeedConfig("ledgerinsights", "Ledger Insights", "https://www.ledgerinsights.com/feed/", "web3"),
    # ── HK Tech Regulation ──
    FeedConfig("hkma", "HKMA Press Releases", "https://www.hkma.gov.hk/eng/other-information/rss/rss_press-release.xml", "hkma"),
]
