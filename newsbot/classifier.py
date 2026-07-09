"""Gemini materiality classifier: one call per article, one assessment per ticker."""
import json
import logging
import time

import requests

from .models import Article, Assessment
from .prompts import RESPONSE_SCHEMA, SYSTEM_RUBRIC, build_user_prompt

log = logging.getLogger(__name__)

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
VALID_DIRECTIONS = {"up", "down", "unclear"}


def classify(article: Article, tickers: list, cfg) -> list:
    """Return one Assessment per ticker. Raises on unrecoverable API failure."""
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_RUBRIC}]},
        "contents": [{
            "role": "user",
            "parts": [{"text": build_user_prompt(article.headline, article.summary, article.source, tickers)}],
        }],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
        },
    }
    text = _call_with_retry(cfg.gemini_model, cfg.gemini_api_key, payload)
    return parse_response(text, tickers)


def _call_with_retry(model: str, api_key: str, payload: dict, attempts: int = 3) -> str:
    url = API_URL.format(model=model)
    last = None
    for i in range(attempts):
        resp = requests.post(url, json=payload, headers={"x-goog-api-key": api_key}, timeout=60)
        if resp.status_code == 200:
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        last = f"{resp.status_code}: {resp.text[:300]}"
        if resp.status_code in (429, 500, 503):
            wait = 2 ** (i + 1)
            log.warning("Gemini %s, retrying in %ss", resp.status_code, wait)
            time.sleep(wait)
            continue
        break
    raise RuntimeError(f"Gemini call failed: {last}")


def parse_response(text: str, requested_tickers: list) -> list:
    """Parse and validate model JSON. Malformed entries fail closed (non-material)."""
    try:
        data = json.loads(text)
        raw = data.get("assessments", [])
    except (json.JSONDecodeError, AttributeError):
        log.error("Unparseable classifier output: %.200s", text)
        raw = []

    by_ticker = {}
    for item in raw:
        try:
            t = str(item["ticker"]).upper().strip()
            conf = max(0.0, min(1.0, float(item["confidence"])))
            direction = str(item["direction"]).lower()
            if direction not in VALID_DIRECTIONS:
                direction = "unclear"
            by_ticker[t] = Assessment(
                ticker=t,
                material=bool(item["material"]),
                confidence=conf,
                direction=direction,
                category=str(item.get("category", "none")),
                reasoning=str(item.get("reasoning", ""))[:400],
            )
        except (KeyError, TypeError, ValueError):
            continue

    out = []
    for t in requested_tickers:
        out.append(by_ticker.get(t.upper()) or Assessment(
            ticker=t, material=False, confidence=0.0,
            direction="unclear", category="none",
            reasoning="fail-closed: missing/malformed assessment",
        ))
    return out


def passes_gate(a: Assessment, cfg) -> bool:
    """Conservative threshold gate. Tune cfg.confidence_threshold from the scorecard."""
    return a.material and a.confidence >= cfg.confidence_threshold
