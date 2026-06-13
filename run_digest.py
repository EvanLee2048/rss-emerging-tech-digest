#!/usr/bin/env python3
"""RSS Emerging Tech Digest — end-to-end pipeline entry point.

Usage:
    # Full pipeline (all feeds, default config)
    python run_digest.py

    # Single category
    python run_digest.py --category ai

    # Dry-run (skip LLM calls, use RSS summaries only)
    python run_digest.py --dry-run

    # Custom config
    python run_digest.py --config /path/to/config.yaml

    # Save digest to file
    python run_digest.py --output /path/to/digest.txt

Environment variables:
    LLM_API_KEY     Required. OpenAI-compatible API key.
    LLM_BASE_URL    Optional. API base URL (default: https://api.openai.com/v1)
    LLM_MODEL       Optional. Model name (default: gpt-4o-mini)
    DIGEST_STATE_DIR Optional. Watermark state directory (default: ~/.digest-state/)
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from src.feeds import fetch_feed, get_feeds
from src.watermark import WatermarkStore
from src.jina_fetcher import enrich_article
from src.llm_client import LLMClient
from src.dedup import semantic_dedup
from src.hkma_filter import filter_all
from src.summarizer import summarize_article
from src.director_briefing import generate_briefing
from src.digest_assembler import assemble_digest
from src.types import Article, CATEGORY_MAP


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="RSS Emerging Tech Digest — daily intelligence pipeline"
    )
    p.add_argument(
        "--category",
        choices=list(CATEGORY_MAP.keys()) + ["all"],
        default="all",
        help="Filter to a single feed category (default: all)",
    )
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip LLM calls and Jina fetches; use RSS summaries only",
    )
    p.add_argument(
        "--config",
        type=str,
        default="",
        help="Path to config.yaml (optional; env vars are used otherwise)",
    )
    p.add_argument(
        "--output",
        type=str,
        default="",
        help="Path to save the digest text (printed to stdout if omitted)",
    )
    p.add_argument(
        "--state-dir",
        type=str,
        default=os.environ.get(
            "DIGEST_STATE_DIR",
            str(Path.home() / ".digest-state"),
        ),
        help="Watermark state directory (default: ~/.digest-state/)",
    )
    p.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="HTTP timeout in seconds (default: 30)",
    )
    p.add_argument(
        "--email-to",
        type=str,
        nargs="?",
        const="__flag_only__",
        default="",
        help="Email recipient (defaults to SMTP_TARGET env var if omitted). Requires SMTP_* env vars.",
    )
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    # ── Step 0: Initialise ──────────────────────────────────────────
    feeds = get_feeds(args.category)
    if not feeds:
        print(f"No feeds found for category: {args.category}", file=sys.stderr)
        return 1

    # Resolve email target: CLI flag takes priority, fallback to env var
    email_to = args.email_to
    if email_to == "__flag_only__":
        email_to = os.environ.get("SMTP_TARGET", "")
    elif not email_to:
        email_to = os.environ.get("SMTP_TARGET", "")

    wm = WatermarkStore(args.state_dir)
    wm.load()

    if not args.dry_run:
        try:
            llm = LLMClient(timeout=args.timeout)
        except ValueError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            print(
                "Set LLM_API_KEY environment variable, or use --dry-run to skip LLM.",
                file=sys.stderr,
            )
            return 1
    else:
        llm = None  # type: ignore[assignment]

    # ── Step 1: Fetch feeds + URL-level dedup ───────────────────────
    all_new_articles: list[Article] = []
    for feed_cfg in feeds:
        fetched = fetch_feed(feed_cfg, timeout=args.timeout)
        if fetched is None:
            continue
        new_articles = wm.filter_new_articles(fetched)
        all_new_articles.extend(new_articles)
        wm.save(feed_cfg.watcher_name)  # Persist watermark after each feed

    if not all_new_articles:
        return 0  # Silent exit — nothing new

    feeds_scanned = len(feeds)
    categories_with_new = list(
        {a.category for a in all_new_articles}
    )

    # ── Step 2: Fetch full article content (Jina) ───────────────────
    if not args.dry_run:
        for i, article in enumerate(all_new_articles):
            enrich_article(article, timeout=args.timeout)
            # Rate-limit: max 5 concurrent Jina requests
            if i > 0 and i % 5 == 0:
                import time as _time
                _time.sleep(2)

    # ── Step 3: Semantic dedup (LLM) ────────────────────────────────
    if llm and not args.dry_run and len(all_new_articles) > 1:
        all_new_articles = semantic_dedup(all_new_articles, llm)

    if not all_new_articles:
        return 0

    # ── Step 4: HKMA relevance filter ───────────────────────────────
    if llm and not args.dry_run:
        all_new_articles = filter_all(all_new_articles, llm)

    if not all_new_articles:
        return 0

    # ── Step 5: Summarize per article ────────────────────────────────
    if llm and not args.dry_run:
        for article in all_new_articles:
            article.bullets = summarize_article(article, llm)

    # ── Step 6: Director Briefing per article ───────────────────────
    if llm and not args.dry_run:
        for article in all_new_articles:
            article.director_briefing = generate_briefing(article, llm)

    # ── Step 7: Assemble digest ─────────────────────────────────────
    digest = assemble_digest(
        all_new_articles,
        feeds_scanned=feeds_scanned,
        categories_with_new=categories_with_new,
    )

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(digest, encoding="utf-8")
        print(f"Digest saved to {out_path}", file=sys.stderr)
    else:
        print(digest)

    # ── Email delivery (optional) ───────────────────────────────────
    if email_to:
        from src.emailer import email_digest
        try:
            email_digest(digest, email_to)
            print(f"Digest emailed to {email_to}", file=sys.stderr)
        except Exception as exc:
            print(
                f"WARNING: Failed to email digest: {exc}",
                file=sys.stderr,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
