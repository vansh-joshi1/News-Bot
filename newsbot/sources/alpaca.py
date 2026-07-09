"""Alpaca News API (v1beta1). Free with any Market Data account; tags tickers natively.

We fetch market-wide news since the watermark and filter to the watchlist locally
(passing 500 symbols in the query string would blow URL length limits).
"""
import logging
from datetime import datetime, timezone

import requests

from ..models import Article

log = logging.getLogger(__name__)
URL = "https://data.alpaca.markets/v1beta1/news"
MAX_PAGES = 10  # safety valve: 10 * 50 articles per run


def fetch(since: datetime, cfg) -> list:
    headers = {
        "APCA-API-KEY-ID": cfg.alpaca_key_id,
        "APCA-API-SECRET-KEY": cfg.alpaca_secret,
    }
    params = {
        "start": since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "limit": 50,
        "sort": "asc",
        "include_content": "false",
    }
    articles, pages = [], 0
    while pages < MAX_PAGES:
        resp = requests.get(URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        for item in data.get("news", []):
            articles.append(_to_article(item))
        token = data.get("next_page_token")
        if not token:
            break
        params["page_token"] = token
        pages += 1
    log.info("alpaca: fetched %d articles since %s", len(articles), params["start"])
    return articles


def _to_article(item: dict) -> Article:
    ts = item.get("updated_at") or item.get("created_at")
    published = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return Article(
        id=f"alpaca:{item['id']}",
        source="alpaca",
        headline=item.get("headline", ""),
        summary=item.get("summary", ""),
        url=item.get("url", ""),
        tickers=tuple(item.get("symbols", [])),
        published_at=published,
    )
