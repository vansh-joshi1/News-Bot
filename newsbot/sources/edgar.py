"""SEC EDGAR source — PHASE 2 STUB.

Plan (free, requires a descriptive User-Agent header per SEC policy):
- Poll https://efts.sec.gov/LATEST/search-index?q=... full-text search for recent
  8-K filings (items 1.01 material agreements, 2.02 results, 5.02 exec changes)
  and Form 4s from watchlist CIKs.
- Maintain a ticker->CIK map from https://www.sec.gov/files/company_tickers.json.
- Headline = "{ticker} 8-K item {n}: {summary}"; the classifier rubric handles the rest.
"""
from datetime import datetime


def fetch(since: datetime, cfg) -> list:
    raise NotImplementedError("Phase 2: enable in Config.enabled_sources once implemented")
