# market-mover-bot

A Discord bot that watches financial news for S&P 500 names and posts an alert **only**
when a story is likely to meaningfully move the stock — up or down. It is a filter,
not a headline firehose: it is deliberately biased toward false negatives.

Not financial advice. The scorecard exists precisely because LLM direction calls
must earn trust empirically before anyone acts on them.

## How it works

Every 5 minutes (GitHub Actions cron):

```
Alpaca News ─► S&P 500 filter ─► dedup (exact + fuzzy) ─► rule pre-filter
        ─► Gemini materiality classifier ─► confidence gate (≥0.85) ─► Discord webhook
```

Every alert is logged to `data/alerts.csv`. A daily job checks the price at T+1 day and
T+1 week and writes hit rates (overall and by confidence bucket) to `data/scorecard.md`.
The S&P 500 list refreshes weekly. All state lives in `data/` and is committed back to
the repo by the workflows.

## Setup (~15 minutes, all free)

### 1. Accounts and keys

- **Alpaca** — sign up at https://alpaca.markets (paper account is fine). Dashboard →
  API Keys → generate. You need the **key ID** and **secret**.
- **Gemini** — https://aistudio.google.com → Get API key. Free tier is enough at this
  alert volume.
- **Discord webhook** — in your server: channel → Edit Channel → Integrations →
  Webhooks → New Webhook → Copy Webhook URL.
- **Finnhub** (phase 2, optional for now) — https://finnhub.io free tier.

### 2. GitHub repo

Create a repo and push this project to it.

> **Actions minutes**: public repos get unlimited free Actions minutes; private repos get
> 2,000/month, which a 5-minute cron will exceed (~9,000 runs/mo × ~1 min). If the repo
> must be private, change `poll.yml` to `*/15 * * * *` and/or restrict to
> market hours, e.g. `"*/5 13-21 * * 1-5"` (13:00–21:59 UTC ≈ US trading day).

Repo → Settings → Secrets and variables → Actions → add:

| Secret | Value |
|---|---|
| `ALPACA_API_KEY_ID` | Alpaca key ID |
| `ALPACA_API_SECRET_KEY` | Alpaca secret |
| `GEMINI_API_KEY` | Google AI Studio key |
| `DISCORD_WEBHOOK_URL` | Discord webhook URL |

Then: Actions tab → enable workflows → run `poll-news` once via *Run workflow* to verify.

### 3. Local dry run (optional but recommended first)

```bash
pip install -r requirements.txt
cp .env.example .env      # fill in keys
export $(grep -v '^#' .env | xargs)
DRY_RUN=1 python -m newsbot.main    # prints would-be alerts, writes nothing
```

Run tests: `pip install pytest && pytest`

## Tuning

- `CONFIDENCE_THRESHOLD` (default 0.85) — the gate. Raise for fewer alerts. Lower it
  **only** after `data/scorecard.md` shows hit rate rising with confidence.
- `MAX_LLM_CALLS_PER_RUN` (default 15) — protects the Gemini free-tier quota; overflow
  articles are logged and skipped.
- `UNMATCHED_POLICY` (default `drop`) — headlines matching neither signal nor noise
  rules are dropped. Set to `llm` to classify them instead (more coverage, more quota).
- The rubric itself lives in `newsbot/prompts.py`; the cheap keyword rules in
  `newsbot/prefilter.py`.

## Roadmap (phase 2)

`newsbot/sources/finnhub.py` and `newsbot/sources/edgar.py` are stubs with implementation
plans in their docstrings. Wire them, add to `Config.enabled_sources`, and dedup collapses
cross-source duplicates automatically.
