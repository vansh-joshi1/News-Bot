"""Core data types."""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class Article:
    id: str                 # source-prefixed, e.g. "alpaca:41234567"
    source: str             # "alpaca" | "finnhub" | "edgar"
    headline: str
    summary: str
    url: str
    tickers: tuple          # tickers tagged by the source
    published_at: datetime  # tz-aware UTC


@dataclass
class Assessment:
    """One LLM materiality call for one (article, ticker) pair."""
    ticker: str
    material: bool
    confidence: float       # 0-1
    direction: str          # "up" | "down" | "unclear"
    category: str           # rubric category, e.g. "earnings_surprise"
    reasoning: str          # one line


@dataclass
class Alert:
    article: Article
    assessment: Assessment
