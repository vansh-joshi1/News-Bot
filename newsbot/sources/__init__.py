"""News sources. Each module exposes fetch(since: datetime, cfg) -> list[Article]."""
from . import alpaca

REGISTRY = {
    "alpaca": alpaca.fetch,
    # Phase 2 — wired but not enabled in Config.enabled_sources:
    # "finnhub": finnhub.fetch,
    # "edgar": edgar.fetch,
}
