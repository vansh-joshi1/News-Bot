"""Discord delivery via channel webhook (post-only, no bot token needed)."""
import logging
import time

import requests

from .models import Alert

log = logging.getLogger(__name__)

COLORS = {"up": 0x2ECC71, "down": 0xE74C3C, "unclear": 0x95A5A6}
ARROWS = {"up": "▲ UP", "down": "▼ DOWN", "unclear": "◆ UNCLEAR"}


def post_alert(webhook_url: str, alert: Alert) -> None:
    a, art = alert.assessment, alert.article
    embed = {
        "title": f"${a.ticker} — {art.headline[:230]}",
        "url": art.url or None,
        "description": a.reasoning,
        "color": COLORS[a.direction],
        "fields": [
            {"name": "Direction", "value": ARROWS[a.direction], "inline": True},
            {"name": "Confidence", "value": f"{a.confidence:.0%}", "inline": True},
            {"name": "Category", "value": a.category.replace("_", " "), "inline": True},
        ],
        "footer": {"text": f"source: {art.source}"},
        "timestamp": art.published_at.isoformat(),
    }
    resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
    if resp.status_code == 429:  # webhook rate limit — wait and retry once
        time.sleep(float(resp.json().get("retry_after", 2)))
        resp = requests.post(webhook_url, json={"embeds": [embed]}, timeout=15)
    resp.raise_for_status()
    log.info("posted alert %s %s", a.ticker, a.direction)
