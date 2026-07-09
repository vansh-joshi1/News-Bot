"""Finnhub source — PHASE 2 STUB.

Plan (free tier, 60 calls/min):
- /company-news for watchlist names flagged by recent volume (not all 500 per run)
- /stock/insider-transactions for unusually large Form 4 activity
- /stock/upgrade-downgrade for analyst actions with PT changes
Map each into models.Article with source="finnhub"; dedup layer collapses overlap
with Alpaca automatically.
"""
from datetime import datetime


def fetch(since: datetime, cfg) -> list:
    raise NotImplementedError("Phase 2: enable in Config.enabled_sources once implemented")
