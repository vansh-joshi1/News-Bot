"""Refresh the cached S&P 500 constituent list. Run weekly (workflow) or manually."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from newsbot.config import load_config  # noqa: E402
from newsbot.watchlist import refresh  # noqa: E402

if __name__ == "__main__":
    cfg = load_config()
    n = refresh(cfg.sp500_csv)
    print(f"wrote {n} constituents to {cfg.sp500_csv}")
