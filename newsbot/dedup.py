"""Dedup: collapse the same story across sources/rewrites into one alert.

Two layers:
1. Exact — sha1 of (normalized headline + sorted tickers).
2. Fuzzy — SequenceMatcher ratio vs. recent headlines sharing >=1 ticker.

Seen entries persist in a JSONL file (committed back to the repo by the
workflow) and are pruned past the dedup window.
"""
import hashlib
import json
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

_PUNCT = re.compile(r"[^a-z0-9 ]+")
_WS = re.compile(r"\s+")
_SUFFIX = re.compile(r"\s*[-|:]\s*(reuters|bloomberg|benzinga|marketwatch|barrons?|wsj|cnbc)\s*$", re.I)


def normalize(headline: str) -> str:
    t = _SUFFIX.sub("", headline.lower())
    t = _PUNCT.sub(" ", t)
    return _WS.sub(" ", t).strip()


def exact_key(headline: str, tickers) -> str:
    basis = normalize(headline) + "|" + ",".join(sorted(tickers))
    return hashlib.sha1(basis.encode()).hexdigest()


class SeenStore:
    def __init__(self, path: Path, window_hours: int = 48, fuzzy_threshold: float = 0.90):
        self.path = path
        self.window_s = window_hours * 3600
        self.fuzzy_threshold = fuzzy_threshold
        self.entries = []  # {key, title, tickers, ts}
        self._keys = set()
        if path.exists():
            now = time.time()
            for line in path.read_text().splitlines():
                if not line.strip():
                    continue
                e = json.loads(line)
                if now - e["ts"] <= self.window_s:
                    self.entries.append(e)
                    self._keys.add(e["key"])

    def seen(self, headline: str, tickers) -> bool:
        if exact_key(headline, tickers) in self._keys:
            return True
        norm = normalize(headline)
        tset = set(tickers)
        for e in self.entries:
            if not tset & set(e["tickers"]):
                continue
            if SequenceMatcher(None, norm, e["title"]).ratio() >= self.fuzzy_threshold:
                return True
        return False

    def add(self, headline: str, tickers) -> None:
        key = exact_key(headline, tickers)
        if key in self._keys:
            return
        self._keys.add(key)
        self.entries.append(
            {"key": key, "title": normalize(headline), "tickers": sorted(tickers), "ts": time.time()}
        )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = time.time()
        keep = [e for e in self.entries if now - e["ts"] <= self.window_s]
        self.path.write_text("".join(json.dumps(e) + "\n" for e in keep))
