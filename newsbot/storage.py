"""State persistence: watermark + alert log. Everything lives under data/ and is
committed back to the repo by the workflow, so state survives stateless cron runs
and stays human-inspectable."""
import csv
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .models import Alert

ALERT_COLUMNS = [
    "id", "alert_ts", "ticker", "direction", "confidence", "category",
    "headline", "url", "baseline_date", "baseline_close",
    "t1d_date", "t1d_close", "t1d_pct", "t1d_correct",
    "t1w_date", "t1w_close", "t1w_pct", "t1w_correct",
]


def get_watermark(path: Path, first_run_lookback_minutes: int) -> datetime:
    if path.exists():
        return datetime.fromisoformat(path.read_text().strip())
    return datetime.now(timezone.utc) - timedelta(minutes=first_run_lookback_minutes)


def set_watermark(path: Path, ts: datetime) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ts.astimezone(timezone.utc).isoformat())


def append_alert(path: Path, alert: Alert) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    new = not path.exists()
    a, art = alert.assessment, alert.article
    alert_id = hashlib.sha1(f"{art.id}|{a.ticker}".encode()).hexdigest()[:12]
    with path.open("a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALERT_COLUMNS)
        if new:
            w.writeheader()
        w.writerow({
            "id": alert_id,
            "alert_ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "ticker": a.ticker,
            "direction": a.direction,
            "confidence": f"{a.confidence:.2f}",
            "category": a.category,
            "headline": art.headline[:300],
            "url": art.url,
        })


def read_alerts(path: Path) -> list:
    if not path.exists():
        return []
    with path.open() as f:
        return list(csv.DictReader(f))


def write_alerts(path: Path, rows: list) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=ALERT_COLUMNS)
        w.writeheader()
        w.writerows(rows)
