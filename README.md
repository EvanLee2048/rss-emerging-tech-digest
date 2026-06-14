# Emerging Tech News Analysis

End-to-end pipeline that polls 10 RSS feeds → fetches full article content → semantic dedup → HKMA relevance filter → per-story LLM summary → Strategic Director Briefing (5-hat framework) → assembled digest → HTML newsletter email.

**Sources:** SemiAnalysis, Import AI, Latent Space, VentureBeat, Gradient Flow, InfoQ, Dark Reading, Payments Dive, Ledger Insights, HKMA Press Releases

Presentation Website: https://evanlee2048.github.io/rss-emerging-tech-digest/

---

## Requirements

- **Ubuntu 20.04+** (or any Linux with Python 3.10+)
- **Python 3.10+** (Python 3.12 recommended)
- **pip** (Python package manager)
- **LLM API key** from any OpenAI-compatible provider (DeepSeek, OpenAI, OpenRouter, local vLLM, etc.)

---

## Installation

### 1. Install Python 3.10+ (if not already installed)

```bash
# Check your Python version
python3 --version

# If < 3.10, install Python 3.12 on Ubuntu:
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

### 2. Clone or copy the script

```bash
# If provided as a tarball or zip:
unzip rss-emerging-tech-digest-script.zip -d ~/rss-digest
cd ~/rss-digest
```

Or copy the directory:

```bash
cp -r /path/to/rss-emerging-tech-digest ~/rss-digest
cd ~/rss-digest
```

### 3. Create a virtual environment (recommended)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install dependencies

```bash
pip install -r requirements.txt
```

### 5. Configure environment variables

Set your LLM API key (required). Add these to your `~/.bashrc`:

```bash
# Required: DeepSeek API key (or any OpenAI-compatible provider)
export LLM_API_KEY="sk-your-deepseek-key"

# Optional: Custom API endpoint (defaults to https://api.deepseek.com/v1)
# export LLM_BASE_URL="https://api.deepseek.com/v1"

# Optional: Model name (defaults to deepseek-v4-flash)
# export LLM_MODEL="deepseek-v4-flash"
```

Apply to current shell:

```bash
source ~/.bashrc
```

---

## Usage

### Quick test (dry run — no LLM calls)

```bash
source .venv/bin/activate
python run_digest.py --dry-run
```

### Full pipeline (with LLM analysis)

```bash
python run_digest.py
```

### Filter by category

```bash
# AI & Digital Transformation only
python run_digest.py --category ai

# HK Tech Regulation only
python run_digest.py --category hkma
```

### Date filter (default: last 2 days)

```bash
# Only articles from last 2 days
python run_digest.py --max-days 2

# Only articles from last 24 hours
python run_digest.py --max-days 1

# No date limit
python run_digest.py --max-days 0
```

### Save output to file

```bash
python run_digest.py --output ~/digest-$(date +%Y%m%d).txt
```

### Jina proxy mode (EC2/cloud)

On cloud infrastructure, sites commonly block datacenter IPs. Use `--jina-proxy` to skip direct fetch and go straight to the Jina AI Reader proxy:

```bash
python run_digest.py --jina-proxy
```

### Email the digest (HTML newsletter)

```bash
# Configure SMTP environment variables first
export SMTP_HOST="smtp.163.com"
export SMTP_PORT=465
export SMTP_USER="your-email@163.com"
export SMTP_PASSWORD="your-auth-code"
export SMTP_TARGET="recipient@example.com"

# Run and email the digest (uses SMTP_TARGET)
python run_digest.py --email-to
```

The email is sent as **multipart/alternative** with:
- **HTML version** — 600px table layout, dark header, coral accents, Consulting Insight boxes, dark mode support
- **Plain text fallback** — for mail clients that block HTML

Subject line format: **`YYYY-MM-DD Em-tech news summary`** (e.g., `2026-06-13 Em-tech news summary`)

### Show help

```bash
python run_digest.py --help
```

---

## Scheduling with Cron (Daily)

To run every morning at 9:00 AM:

```bash
crontab -e
```

Add at the top (env vars) and the cron line:

```cron
LLM_API_KEY=sk-your-deepseek-key
SMTP_HOST=smtp.163.com
SMTP_PORT=465
SMTP_USER=your-email@163.com
SMTP_PASSWORD=your-auth-code
SMTP_TARGET=recipient@example.com

0 9 * * * cd ~/rss-digest && .venv/bin/python run_digest.py --max-days 1 --jina-proxy --email-to >> ~/rss-digest/digest.log 2>&1
```

---

## Configuration Reference

### Environment Variables

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | *(required)* | OpenAI-compatible API key (e.g., DeepSeek) |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | API endpoint base URL |
| `LLM_MODEL` | `deepseek-v4-flash` | Model name for LLM calls |

### Email Configuration

| Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | `smtp.163.com` | SMTP server hostname |
| `SMTP_PORT` | `465` | SMTP server port (SSL) |
| `SMTP_USER` | *(required)* | SMTP username (your email) |
| `SMTP_PASSWORD` | *(required)* | SMTP password or 授权码 |
| `SMTP_FROM` | `$SMTP_USER` | From email address |
| `SMTP_TARGET` | — | Default recipient (used when `--email-to` is passed without value) |

### CLI Flags

| Flag | Default | Description |
|---|---|---|
| `--category` | `all` | Feed category filter (`all`, `ai`, `cyber`, `fintech`, `web3`, `hkma`) |
| `--dry-run` | `false` | Skip LLM/Jina calls, use RSS summaries only |
| `--output PATH` | stdout | Save digest to file |
| `--timeout SEC` | `120` | HTTP/SMTP timeout for RSS/Jina/LLM requests |
| `--email-to EMAIL` | — | Email recipient (defaults to `SMTP_TARGET` env var if omitted) |
| `--max-days N` | `2` | Only process articles published within N days. `0` = no limit |
| `--jina-proxy` | `false` | Skip direct fetch, use Jina AI Reader proxy directly. Use on EC2/cloud |

---

## Project Structure

```
rss-emerging-tech-digest/
├── run_digest.py          # Main entry point
├── config.yaml            # Configuration template
├── requirements.txt       # Python dependencies (pytest only)
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── types.py           # Data types & feed definitions
│   ├── feeds.py           # RSS feed fetching & parsing
│   ├── jina_fetcher.py    # Article content fetch (direct + Jina fallback)
│   ├── llm_client.py      # OpenAI-compatible LLM client
│   ├── dedup.py           # Cross-feed semantic dedup
│   ├── hkma_filter.py     # HKMA relevance filter
│   ├── summarizer.py      # Article summarization
│   ├── director_briefing.py # Strategic Director Briefing
│   ├── digest_assembler.py  # Final digest assembly
│   └── emailer.py           # SMTP email delivery (HTML + plain text)
└── tests/
    ├── test_types.py
    ├── test_feeds.py
    ├── test_jina_fetcher.py
    ├── test_llm_client.py
    ├── test_dedup.py
    ├── test_hkma_filter.py
    ├── test_summarizer.py
    ├── test_director_briefing.py
    ├── test_digest_assembler.py
    ├── test_emailer.py
    ├── test_date_parsing.py
    ├── test_integration.py
    ├── demo_output.py
    └── demo_preview_html.py
```

---

## Testing

```bash
source .venv/bin/activate
pip install pytest
pytest tests/ -v
```

---

## How It Works

```
Feeds → date filter (--max-days) → Jina full-article fetch (or direct)
→ LLM semantic dedup (cross-feed) → HKMA relevance filter
→ LLM summarization (≤10 bullets, ≤150w, retain figures/names)
→ Director Briefing (5-hat framework, ≤150w)
→ Assemble digest → HTML newsletter email
```

1. **Date Filter** — Fetches articles from RSS feeds, drops any older than `--max-days`. No persistent state needed.
2. **Full-Article Fetch** — Tries direct HTTP fetch first. Falls back to Jina AI Reader proxy (bypasses Cloudflare). Use `--jina-proxy` on EC2 to skip direct attempts.
3. **Semantic Dedup** — LLM compares articles across feeds, keeping only the most authoritative source for each unique story.
4. **HKMA Filter** — LLM filters HKMA press releases for strategic regulatory content, dropping operational/routine items.
5. **Summarize** — LLM produces tight bullet-point summaries (≤10 bullets, ≤150 words) retaining all figures, names, and examples.
6. **Director Briefing** — Consulting Director persona applies 5 hats (Sales, Strategist, Architect, Product, Project) per article.
7. **Assemble** — Formats the digest and sends as an HTML newsletter with dark mode support.

---

## LLM Provider Options

The script uses **OpenAI-compatible API format** — works with any provider that implements `/v1/chat/completions`:

| Provider | Base URL | Notes |
|---|---|---|
| **DeepSeek** (default) | `https://api.deepseek.com/v1` | Set `LLM_API_KEY` to your DeepSeek key |
| **OpenAI** | `https://api.openai.com/v1` | Override via `LLM_BASE_URL` and `LLM_MODEL` |
| **OpenRouter** | `https://openrouter.ai/api/v1` | Access many models with one key |
| **Local vLLM** | `http://localhost:8000/v1` | Self-hosted, no data leaves your machine |

For best results, use a model with ≥8K context window and ≥512 token output.

---

## Troubleshooting

**Problem:** `LLM_API_KEY not set`
→ Export the environment variable or set it in `~/.bashrc`.

**Problem:** `SMTP_USER and SMTP_PASSWORD must be set`
→ These are required when using `--email-to`. Export `SMTP_USER` and `SMTP_PASSWORD` (or 授权码).

**Problem:** `No recipient — set SMTP_TARGET or pass --email-to`
→ The target email address is required. Either set `SMTP_TARGET` env var or pass `--email-to recipient@example.com`.

**Problem:** Direct fetch returns Cloudflare block on EC2
→ Add `--jina-proxy` to route all article fetches through the Jina AI Reader proxy.

**Problem:** `ModuleNotFoundError: No module named 'src'`
→ Run from the project root directory (`rss-emerging-tech-digest/`).
