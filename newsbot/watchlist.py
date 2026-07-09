"""S&P 500 constituents. Cached as data/sp500.csv; auto-downloaded when missing
and refreshed weekly by a workflow from the maintained `datasets/s-and-p-500-companies`
public dataset."""
import csv
import io

import requests

SOURCE_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"


def refresh(dest) -> int:
    resp = requests.get(SOURCE_URL, timeout=30)
    resp.raise_for_status()
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    symbols = [r["Symbol"].strip() for r in rows if r.get("Symbol", "").strip()]
    if len(symbols) < 400:  # sanity check before overwriting a good list
        raise ValueError(f"Refused to write suspicious constituent list ({len(symbols)} symbols)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with dest.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Symbol", "Name", "Sector"])
        for r in rows:
            w.writerow([r["Symbol"].strip(), r.get("Security", "").strip(), r.get("GICS Sector", "").strip()])
    return len(symbols)


def load(path) -> set:
    """Return the watchlist as a set of tickers, downloading it if absent."""
    if not path.exists():
        refresh(path)
    with path.open() as f:
        return {row["Symbol"].strip() for row in csv.DictReader(f) if row.get("Symbol", "").strip()}
