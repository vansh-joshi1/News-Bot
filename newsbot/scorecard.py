"""Accuracy scorecard: evaluates every alert at T+1 trading day and T+1 week.

Prices come from Stooq (free, no key). Baseline = last close strictly before the
alert date, so the alert-day reaction itself is captured in the T+1d move.
Correctness:
  up/down  -> sign of the % move matches the call
  unclear  -> |move| >= cfg.meaningful_move_pct (the call was "this will move")

Run daily after US close: python -m newsbot.scorecard
"""
import csv
import io
import logging
import sys
from datetime import date, datetime, timedelta

import requests

from .config import load_config
from .storage import read_alerts, write_alerts

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("scorecard")

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}&i=d&d1={d1}&d2={d2}"
_price_cache = {}


def stooq_symbol(ticker: str) -> str:
    return ticker.lower().replace(".", "-") + ".us"


def fetch_closes(ticker: str, start: date, end: date) -> dict:
    """date -> close, from Stooq daily CSV."""
    key = (ticker, start, end)
    if key in _price_cache:
        return _price_cache[key]
    url = STOOQ_URL.format(symbol=stooq_symbol(ticker),
                           d1=start.strftime("%Y%m%d"), d2=end.strftime("%Y%m%d"))
    resp = requests.get(url, timeout=30)
    closes = {}
    if resp.ok and resp.text.startswith("Date"):
        for row in csv.DictReader(io.StringIO(resp.text)):
            try:
                closes[date.fromisoformat(row["Date"])] = float(row["Close"])
            except (KeyError, ValueError):
                continue
    _price_cache[key] = closes
    return closes


def _close_on_or_after(closes: dict, target: date):
    for d in sorted(closes):
        if d >= target:
            return d, closes[d]
    return None, None


def _close_before(closes: dict, target: date):
    prior = [d for d in sorted(closes) if d < target]
    if not prior:
        return None, None
    return prior[-1], closes[prior[-1]]


def _correct(direction: str, pct: float, meaningful: float) -> str:
    if direction == "up":
        return str(pct > 0)
    if direction == "down":
        return str(pct < 0)
    return str(abs(pct) >= meaningful)


def evaluate(rows: list, cfg, today: date) -> int:
    updated = 0
    for r in rows:
        if r["t1d_correct"] and r["t1w_correct"]:
            continue
        alert_date = datetime.fromisoformat(r["alert_ts"]).date()
        closes = fetch_closes(r["ticker"], alert_date - timedelta(days=7), today)
        if not closes:
            log.warning("no price data for %s", r["ticker"])
            continue
        if not r["baseline_close"]:
            bd, bc = _close_before(closes, alert_date)
            if bc is None:
                continue
            r["baseline_date"], r["baseline_close"] = bd.isoformat(), f"{bc:.2f}"
        base = float(r["baseline_close"])
        for prefix, offset in (("t1d", 1), ("t1w", 7)):
            if r[f"{prefix}_correct"]:
                continue
            target = alert_date + timedelta(days=offset)
            if today < target:
                continue
            d, c = _close_on_or_after(closes, target)
            if c is None:
                continue
            pct = (c - base) / base * 100
            r[f"{prefix}_date"] = d.isoformat()
            r[f"{prefix}_close"] = f"{c:.2f}"
            r[f"{prefix}_pct"] = f"{pct:+.2f}"
            r[f"{prefix}_correct"] = _correct(r["direction"], pct, cfg.meaningful_move_pct)
            updated += 1
    return updated


def summarize(rows: list) -> str:
    lines = ["# Scorecard", ""]
    lines.append(f"Total alerts: {len(rows)}")
    for prefix, label in (("t1d", "T+1 day"), ("t1w", "T+1 week")):
        done = [r for r in rows if r[f"{prefix}_correct"]]
        if not done:
            lines.append(f"\n## {label}: no evaluated alerts yet")
            continue
        hits = [r for r in done if r[f"{prefix}_correct"] == "True"]
        lines.append(f"\n## {label}: {len(hits)}/{len(done)} correct ({len(hits)/len(done):.0%})")
        lines.append("\n| Confidence | n | hit rate | avg abs move |")
        lines.append("|---|---|---|---|")
        for lo, hi in ((0.85, 0.90), (0.90, 0.95), (0.95, 1.001)):
            bucket = [r for r in done if lo <= float(r["confidence"]) < hi]
            if not bucket:
                continue
            bh = sum(1 for r in bucket if r[f"{prefix}_correct"] == "True")
            avg = sum(abs(float(r[f"{prefix}_pct"])) for r in bucket) / len(bucket)
            lines.append(f"| {lo:.2f}-{hi:.2f} | {len(bucket)} | {bh/len(bucket):.0%} | {avg:.1f}% |")
    lines.append("\nCalibration check: if hit rate doesn't rise with confidence, the rubric "
                 "(not the threshold) needs work.")
    return "\n".join(lines) + "\n"


def run() -> int:
    cfg = load_config()
    rows = read_alerts(cfg.alerts_csv)
    if not rows:
        log.info("no alerts logged yet")
        return 0
    updated = evaluate(rows, cfg, date.today())
    write_alerts(cfg.alerts_csv, rows)
    cfg.scorecard_md.write_text(summarize(rows))
    log.info("evaluated %d checkpoints across %d alerts", updated, len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(run())
