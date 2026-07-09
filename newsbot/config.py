"""Central config. Env vars override defaults; secrets come only from env."""
import os
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"


def _f(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _i(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


@dataclass
class Config:
    # Secrets (from env / GitHub Actions secrets)
    alpaca_key_id: str = field(default_factory=lambda: os.environ.get("ALPACA_API_KEY_ID", ""))
    alpaca_secret: str = field(default_factory=lambda: os.environ.get("ALPACA_API_SECRET_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.environ.get("GEMINI_API_KEY", ""))
    discord_webhook_url: str = field(default_factory=lambda: os.environ.get("DISCORD_WEBHOOK_URL", ""))
    finnhub_api_key: str = field(default_factory=lambda: os.environ.get("FINNHUB_API_KEY", ""))

    # Classifier
    gemini_model: str = field(default_factory=lambda: os.environ.get("GEMINI_MODEL", "gemini-2.5-flash"))
    confidence_threshold: float = field(default_factory=lambda: _f("CONFIDENCE_THRESHOLD", 0.85))
    max_llm_calls_per_run: int = field(default_factory=lambda: _i("MAX_LLM_CALLS_PER_RUN", 15))
    max_tickers_per_article: int = 3

    # Ingestion
    enabled_sources: tuple = ("alpaca",)
    first_run_lookback_minutes: int = 60

    # Dedup
    dedup_window_hours: int = 48
    fuzzy_threshold: float = 0.90

    # Pre-filter: what to do with headlines matching neither signal nor noise
    # rules. "drop" = bias toward false negatives (default). "llm" = classify.
    unmatched_policy: str = field(default_factory=lambda: os.environ.get("UNMATCHED_POLICY", "drop"))

    # Scorecard
    meaningful_move_pct: float = 2.0  # |move| >= this counts as "meaningful" for unclear-direction alerts

    # Paths
    data_dir: Path = DATA_DIR
    sp500_csv: Path = DATA_DIR / "sp500.csv"
    watermark_file: Path = DATA_DIR / "state" / "watermark.txt"
    seen_file: Path = DATA_DIR / "state" / "seen.jsonl"
    alerts_csv: Path = DATA_DIR / "alerts.csv"
    scorecard_md: Path = DATA_DIR / "scorecard.md"

    dry_run: bool = field(default_factory=lambda: os.environ.get("DRY_RUN", "") not in ("", "0", "false"))


def load_config() -> Config:
    return Config()
