# Design: market-mover-bot (approved 2026-07-08)

## Goal
Post a Discord alert only when a news item is likely to move an S&P 500 stock
meaningfully (~≥2% within a week). Bias toward false negatives; trust over volume.
Budget $0; latency target = minutes.

## Decisions
- **Runtime**: GitHub Actions cron every 5 min (accepting 5–15 min scheduler drift).
  Stateless runs; state committed back to the repo under `data/` (dedup cache,
  watermark, alert log, scorecard). Secrets in Actions secrets.
- **LLM**: Gemini Flash free tier, JSON mode with response schema, temperature 0.1.
  One call per article, one assessment per ticker (handles M&A direction splits).
  Fail closed on any parse/API error. Per-run call cap protects free quota.
- **Discord**: channel webhook (post-only), color-coded embeds.
- **Watchlist**: `datasets/s-and-p-500-companies` CSV, cached in repo, weekly refresh,
  sanity check (≥400 symbols) before overwrite.
- **Dedup**: exact sha1(normalized title + tickers) plus SequenceMatcher ≥0.90 against
  48h of same-ticker headlines.
- **Pre-filter**: generous signal regexes (LLM is the judge), conservative noise
  regexes (wrong drops are unrecoverable), unmatched → drop by default.
- **Gate**: material AND confidence ≥ 0.85 (start high; tune from scorecard only).
- **Scorecard**: baseline = last close before alert date; evaluate first close ≥ T+1d
  and ≥ T+7d from Stooq (free, keyless). up/down correct = sign match; unclear
  correct = |move| ≥ 2%. Daily job writes hit rates by confidence bucket to
  `scorecard.md` — calibration check: hit rate must rise with confidence.

## Phase 2
Finnhub (analyst actions, insider transactions, company news) and SEC EDGAR
(8-K items 1.01/2.02/5.02, Form 4) as additional sources behind the same
`fetch(since, cfg) -> list[Article]` interface; stubs document the plan.

## Known trade-offs
- GH Actions cron drift means worst-case ~20 min latency on busy days — accepted.
- Committing state to the repo makes history noisy — accepted for $0 durability.
- Stooq daily closes only (no intraday baseline) — good enough for direction scoring.
