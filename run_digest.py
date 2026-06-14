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
import time
from datetime import datetime
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
        default=120,
        help="HTTP/SMTP timeout in seconds (default: 120)",
    )
    p.add_argument(
        "--email-to",
        type=str,
        nargs="?",
        const="__flag_only__",
        default="",
        help="Email recipient (defaults to SMTP_TARGET env var if omitted). Requires SMTP_* env vars.",
    )
    p.add_argument(
        "--max-days",
        type=int,
        default=2,
        help="Only keep articles published within this many days (default: 2). 0 = no limit.",
    )
    return p.parse_args(argv)


def log(msg: str) -> None:
    """Print a timestamped progress message to stderr."""
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


def main(argv: list[str] | None = None) -> int:
    t_start = time.time()
    args = parse_args(argv)

    # ── Step 0: Initialise ──────────────────────────────────────────
    feeds = get_feeds(args.category)
    if not feeds:
        log(f"ERROR: No feeds found for category '{args.category}'")
        return 1

    log(f"Pipeline started — {len(feeds)} feeds, category={args.category}"
        f"{' (DRY RUN)' if args.dry_run else ''}")

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
            log(f"LLM client ready — model={llm.model}, endpoint={llm.base_url}")
        except ValueError as e:
            log(f"ERROR: {e}")
            log("Set LLM_API_KEY environment variable, or use --dry-run to skip LLM.")
            return 1
    else:
        llm = None  # type: ignore[assignment]
        log("DRY RUN: LLM and Jina calls will be skipped")

    # ── Step 1: Fetch feeds + URL-level dedup ───────────────────────
    log("Step 1/7: Fetching RSS feeds & URL dedup...")
    all_new_articles: list[Article] = []
    feeds_with_new = 0
    for feed_cfg in feeds:
        fetched = fetch_feed(feed_cfg, timeout=args.timeout)
        if fetched is None:
            log(f"  ⚠ {feed_cfg.watcher_name}: fetch failed (skipped)")
            continue
        log(f"  ✓ {feed_cfg.watcher_name}: {len(fetched)} items fetched")
        new_articles = wm.filter_new_articles(fetched)
        if new_articles:
            feeds_with_new += 1
            dated = sum(1 for a in new_articles if a.date)
            log(f"    → {len(new_articles)} new (after URL dedup), "
                f"{dated} with dates, {len(new_articles)-dated} without)")
        all_new_articles.extend(new_articles)
        wm.save(feed_cfg.watcher_name)  # Persist watermark after each feed

    if not all_new_articles:
        log("No new articles found — exiting silently")
        return 0  # Silent exit — nothing new

    feeds_scanned = len(feeds)
    categories_with_new = list({a.category for a in all_new_articles})
    log(f"Step 1 complete — {len(all_new_articles)} new articles from "
        f"{feeds_with_new}/{feeds_scanned} feeds")

    # ── Step 1b: Filter by recency (--max-days) ────────────────────
    if args.max_days > 0:
        from datetime import datetime as _dt, timedelta
        cutoff = _dt.now().date() - timedelta(days=args.max_days)

        # Show date range for diagnostics
        dated = [a for a in all_new_articles if a.date]
        undated = [a for a in all_new_articles if not a.date]
        if dated:
            dates = sorted(set(a.date for a in dated))
            log(f"  Date range in fetched articles: {dates[0]} to {dates[-1]}"
                f" ({len(dated)} with dates, {len(undated)} without)")
        elif undated:
            log(f"  No dates found in any article ({len(undated)} undated)")
        else:
            log("  No articles at all — skipping date filter")

        before = len(all_new_articles)
        all_new_articles = [
            a for a in all_new_articles
            if not a.date or _dt.strptime(a.date, "%Y-%m-%d").date() >= cutoff
        ]
        removed = before - len(all_new_articles)
        if removed:
            log(f"  → {removed} articles older than {args.max_days} days filtered out")
            if dated and removed == before:
                log(f"  ⚠ All articles have dates older than {args.max_days} days.")
                log(f"  ⚠ Try --max-days 30 or higher to capture them, or check if feeds are stale.")
        else:
            log(f"  All {before} articles within {args.max_days}-day window")

        if not all_new_articles:
            log("No articles within the date window — exiting")
            return 0

    # ── Step 2: Fetch full article content (Jina) ───────────────────
    if not args.dry_run:
        log(f"Step 2/7: Fetching full article content via Jina "
            f"({len(all_new_articles)} articles)...")
        for i, article in enumerate(all_new_articles):
            log(f"  Jina {i+1}/{len(all_new_articles)}: \"{article.title[:60]}...\"")
            enrich_article(article, timeout=args.timeout)
            # Rate-limit: max 5 concurrent Jina requests
            if i > 0 and i % 5 == 0:
                log("  Rate-limit pause (2s)...")
                time.sleep(2)
        log("Step 2 complete — full article text fetched")
    else:
        log("Step 2/7: Skipped (dry run)")

    # ── Step 3: Semantic dedup (LLM) ────────────────────────────────
    if llm and not args.dry_run and len(all_new_articles) > 1:
        log(f"Step 3/7: Semantic dedup across feeds ({len(all_new_articles)} articles)...")
        before = len(all_new_articles)
        all_new_articles = semantic_dedup(all_new_articles, llm)
        removed = before - len(all_new_articles)
        log(f"Step 3 complete — {removed} duplicates removed, "
            f"{len(all_new_articles)} unique articles remain")
    else:
        log("Step 3/7: Skipped (dry run or ≤1 article)")

    if not all_new_articles:
        log("All articles filtered out — exiting")
        return 0

    # ── Step 4: HKMA relevance filter ───────────────────────────────
    if llm and not args.dry_run:
        hkma_count = sum(1 for a in all_new_articles if a.feed_key == "hkma")
        log(f"Step 4/7: HKMA relevance filter ({hkma_count} HKMA items)...")
        before = len(all_new_articles)
        all_new_articles = filter_all(all_new_articles, llm)
        filtered = before - len(all_new_articles)
        if filtered:
            log(f"  → {filtered} HKMA items filtered out")
        log(f"Step 4 complete — {len(all_new_articles)} articles remain")
    else:
        log("Step 4/7: Skipped (dry run)")

    if not all_new_articles:
        log("All articles filtered out — exiting")
        return 0

    # ── Step 5: Summarize per article ────────────────────────────────
    if llm and not args.dry_run:
        log(f"Step 5/7: Summarizing {len(all_new_articles)} articles...")
        for i, article in enumerate(all_new_articles):
            log(f"  Summarize {i+1}/{len(all_new_articles)}: \"{article.title[:60]}...\"")
            article.bullets = summarize_article(article, llm)
        log("Step 5 complete — all articles summarized")
    else:
        log("Step 5/7: Skipped (dry run)")

    # ── Step 6: Director Briefing per article ───────────────────────
    if llm and not args.dry_run:
        log(f"Step 6/7: Director Briefing for {len(all_new_articles)} articles...")
        for i, article in enumerate(all_new_articles):
            log(f"  Briefing {i+1}/{len(all_new_articles)}: \"{article.title[:60]}...\"")
            article.director_briefing = generate_briefing(article, llm)
        log("Step 6 complete — all briefings generated")
    else:
        log("Step 6/7: Skipped (dry run)")

    # ── Step 7: Assemble digest ─────────────────────────────────────
    log("Step 7/7: Assembling digest...")
    digest = assemble_digest(
        all_new_articles,
        feeds_scanned=feeds_scanned,
        categories_with_new=categories_with_new,
    )

    elapsed = time.time() - t_start
    log(f"Digest assembled — {len(all_new_articles)} articles, "
        f"elapsed: {elapsed:.0f}s")

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(digest, encoding="utf-8")
        log(f"Digest saved to {out_path}")
    else:
        print(digest)

    # ── Email delivery (optional) ───────────────────────────────────
    if email_to:
        log(f"Delivering via email to {email_to}...")
        from src.emailer import email_digest
        try:
            email_digest(digest, email_to)
            log(f"Email sent to {email_to}")
        except Exception as exc:
            log(f"WARNING: Failed to email digest: {exc}")

    t_total = time.time() - t_start
    log(f"Pipeline finished — total time: {t_total:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
