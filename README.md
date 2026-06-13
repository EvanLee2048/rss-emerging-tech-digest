# RSS Emerging Tech Digest

End-to-end pipeline that polls 10 RSS feeds → fetches full article content (Jina) → semantic dedup → HKMA relevance filter → per-story LLM summary → Strategic Director Briefing (5-hat framework) → assembled digest.

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

Or copy the `rss-emerging-tech-digest-script/` directory to your home:

```bash
cp -r /path/to/rss-emerging-tech-digest-script ~/rss-digest
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

Set your LLM API key (required). Add these to your `~/.bashrc` or `~/.zshrc` for persistence:

```bash
# Required: DeepSeek API key (or any OpenAI-compatible provider)
export LLM_API_KEY="sk-your-deepseek-key"

# Optional: Custom API endpoint (defaults to https://api.deepseek.com/v1)
# export LLM_BASE_URL="https://api.deepseek.com/v1"

# Optional: Model name (defaults to deepseek-v4-flash)
# export LLM_MODEL="deepseek-v4-flash"

# Optional: State directory for watermark files (defaults to ~/.digest-state/)
export DIGEST_STATE_DIR="$HOME/.digest-state"
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

The first run establishes a baseline (records seen articles, emits nothing). Run it again to see new articles:

```bash
python run_digest.py --dry-run
```

### Full pipeline (with LLM analysis)

```bash
source .venv/bin/activate
python run_digest.py
```

### Filter by category

```bash
# AI & Digital Transformation only
python run_digest.py --category ai

# HK Tech Regulation only
python run_digest.py --category hkma
```

### Save output to file

```bash
python run_digest.py --output ~/digest-$(date +%Y%m%d).txt
```

### Email the digest

```bash
# Configure SMTP environment variables first
export SMTP_HOST="smtp.whatevermail.com"
export SMTP_PORT=465
export SMTP_USER="your-email@whatevermail.com"
export SMTP_PASSWORD="your-auth-code"
export SMTP_TARGET="recipient@example.com"

# Run and email the digest (uses SMTP_TARGET)
python run_digest.py --email-to
```

Subject line format: **`YYYY-MM-DD Em-tech news summary`** (e.g., `2026-06-13 Em-tech news summary`)

### Show help

```bash
python run_digest.py --help
```

---

## Scheduling with Cron (Daily)

To run the pipeline automatically every morning at 7:00 AM:

```bash
# Edit your crontab
crontab -e
```

Add this line (adjust paths to match your setup):

```cron
# ── RSS Emerging Tech Digest — daily at 7:00 AM ──
0 7 * * * cd /home/$USER/rss-digest && /home/$USER/rss-digest/.venv/bin/python /home/$USER/rss-digest/run_digest.py --output /home/$USER/digests/$(date +\%Y\%m\%d).txt >> /home/$USER/rss-digest/digest.log 2>&1
```

Create the output directory:

```bash
mkdir -p ~/digests
```

To get the digest delivered by email, add `MAILTO=your@email.com` at the top of your crontab, or use the built-in SMTP delivery:

```cron
# ── RSS Emerging Tech Digest — daily at 7:00 AM with email ──
0 7 * * * cd /home/$USER/rss-digest && /home/$USER/rss-digest/.venv/bin/python /home/$USER/rss-digest/run_digest.py --email-to >> /home/$USER/rss-digest/digest.log 2>&1
```

(Set `SMTP_TARGET` in the environment or crontab for the recipient address.)

---

## Configuration Reference

All settings can be configured via environment variables or the `--config` YAML file.

| Environment Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | *(required)* | OpenAI-compatible API key (e.g., DeepSeek) |
| `LLM_BASE_URL` | `https://api.deepseek.com/v1` | API endpoint base URL |
| `LLM_MODEL` | `deepseek-v4-flash` | Model name for LLM calls |
| `DIGEST_STATE_DIR` | `~/.digest-state/` | Watermark state directory |

### Email Configuration (for `--email-to`)

| Environment Variable | Default | Description |
|---|---|---|
| `SMTP_HOST` | `smtp.whatevermail.com` | SMTP server hostname |
| `SMTP_PORT` | `465` | SMTP server port (SSL) |
| `SMTP_USER` | *(required)* | SMTP username (your email) |
| `SMTP_PASSWORD` | *(required)* | SMTP password or 授权码 |
| `SMTP_FROM` | `$SMTP_USER` | From email address |
| `SMTP_TARGET` | — | Default recipient (used when --email-to is passed without value) |

| CLI Flag | Default | Description |
|---|---|---|
| `--category` | `all` | Feed category filter (`all`, `ai`, `cyber`, `fintech`, `web3`, `hkma`) |
| `--dry-run` | `false` | Skip LLM/Jina calls, use RSS summaries only |
| `--output PATH` | stdout | Save digest to file |
| `--state-dir PATH` | `~/.digest-state/` | Watermark state directory |
| `--timeout SEC` | `30` | HTTP timeout for RSS/Jina/LLM requests |
| `--email-to EMAIL` | — | Email recipient (defaults to SMTP_TARGET env var if omitted) |

---

## Project Structure

```
rss-emerging-tech-digest-script/
├── run_digest.py          # Main entry point
├── config.yaml            # Configuration template
├── requirements.txt       # Python dependencies (pytest only)
├── README.md              # This file
├── src/
│   ├── __init__.py
│   ├── types.py           # Data types & feed definitions
│   ├── watermark.py       # URL-level dedup state management
│   ├── feeds.py           # RSS feed fetching & parsing
│   ├── jina_fetcher.py    # Jina AI full-article fetching
│   ├── llm_client.py      # OpenAI-compatible LLM client
│   ├── dedup.py           # Cross-feed semantic dedup
│   ├── hkma_filter.py     # HKMA relevance filter
│   ├── summarizer.py      # Article summarization
│   ├── director_briefing.py # Strategic Director Briefing
│   ├── digest_assembler.py  # Final digest assembly
│   └── emailer.py           # SMTP email delivery
└── tests/
    ├── test_types.py
    ├── test_feeds.py
    ├── test_watermark.py
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
    └── demo_output.py
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
Feeds → URL-level dedup (watermark) → Jina full-article fetch
→ LLM semantic dedup (cross-feed) → HKMA relevance filter
→ LLM summarization (≤10 bullets, ≤150w, retain figures/names)
→ Director Briefing (5-hat framework, ≤150w)
→ Assemble digest → output
```

1. **URL-Level Dedup** — Records article URL hashes per feed. First run establishes baseline. Subsequent runs emit only unseen URLs.
2. **Full-Article Fetch** — Uses Jina AI Reader proxy to bypass Cloudflare and get rendered plain text from article URLs.
3. **Semantic Dedup** — LLM compares articles across feeds, keeping only the most authoritative source for each unique story.
4. **HKMA Filter** — LLM filters HKMA press releases for strategic regulatory content, dropping operational/routine items.
5. **Summarize** — LLM produces tight bullet-point summaries (≤10 bullets, ≤150 words) retaining all figures, names, and examples.
6. **Director Briefing** — Consulting Director persona applies 5 hats (Sales, Strategist, Architect, Product, Project) per article.
7. **Assemble** — Formats the digest with header, intelligence brief, and footer.

---

## LLM Provider Options

The script uses **OpenAI-compatible API format** — works with any provider that implements `/v1/chat/completions`:

| Provider | Base URL | Notes |
|---|---|---|
| **DeepSeek** (default) | `https://api.deepseek.com/v1` | Set `LLM_API_KEY` to your DeepSeek key |
| **OpenAI** | `https://api.openai.com/v1` | Override via `LLM_BASE_URL` and `LLM_MODEL` |
| **OpenRouter** | `https://openrouter.ai/api/v1` | Access many models with one key |
| **Local vLLM** | `http://localhost:8000/v1` | Self-hosted, no data leaves your machine |
| **Anthropic via proxy** | varies | Use a proxy that translates Anthropic to OpenAI format |

For best results, use a model with ≥8K context window and ≥512 token output. DeepSeek V4 Flash works well — adjust `LLM_MODEL` and `LLM_BASE_URL` to switch providers.

---

## Troubleshooting

**Problem:** `LLM_API_KEY not set`
→ Export the environment variable or set it in `~/.bashrc`.

**Problem:** `SMTP_USER and SMTP_PASSWORD must be set`
→ These are required when using `--email-to`. Export `SMTP_USER` and `SMTP_PASSWORD` (or 授权码 for whatevermail.com).

**Problem:** `No recipient — set SMTP_TARGET or pass --email-to`
→ The target email address is required. Either set `SMTP_TARGET` env var or pass `--email-to recipient@example.com`.

**Problem:** First run produces no output
→ This is expected — the first run records all seen articles so subsequent runs only emit new ones.

**Problem:** Jina returns "Warning: Target URL returned error 403"
→ The article site is blocked even via Jina. The script falls back to the RSS summary text automatically.

**Problem:** `ModuleNotFoundError: No module named 'src'`
→ Run from the project root directory (`rss-emerging-tech-digest-script/`) or install the package.
