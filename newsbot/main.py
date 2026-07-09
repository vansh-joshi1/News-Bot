"""Pipeline runner: one stateless pass, designed for a 5-minute GitHub Actions cron.

fetch -> watchlist filter -> dedup -> rule pre-filter -> Gemini classify ->
threshold gate -> Discord webhook -> persist state.

DRY_RUN=1 prints would-be alerts instead of posting, and skips state writes.
"""
import logging
import sys

from . import sources, watchlist
from .classifier import classify, passes_gate
from .config import load_config
from .dedup import SeenStore
from .models import Alert
from .notify import post_alert
from .prefilter import classify_text
from .storage import append_alert, get_watermark, set_watermark

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
log = logging.getLogger("newsbot")


def run() -> int:
    cfg = load_config()
    missing = [n for n, v in [
        ("ALPACA_API_KEY_ID", cfg.alpaca_key_id),
        ("ALPACA_API_SECRET_KEY", cfg.alpaca_secret),
        ("GEMINI_API_KEY", cfg.gemini_api_key),
    ] if not v]
    if not cfg.dry_run and not cfg.discord_webhook_url:
        missing.append("DISCORD_WEBHOOK_URL")
    if missing:
        log.error("missing required env: %s", ", ".join(missing))
        return 1

    wl = watchlist.load(cfg.sp500_csv)
    seen = SeenStore(cfg.seen_file, cfg.dedup_window_hours, cfg.fuzzy_threshold)
    since = get_watermark(cfg.watermark_file, cfg.first_run_lookback_minutes)

    articles = []
    for name in cfg.enabled_sources:
        try:
            articles.extend(sources.REGISTRY[name](since, cfg))
        except Exception:
            log.exception("source %s failed; continuing", name)

    stats = {"fetched": len(articles), "watchlist": 0, "new": 0,
             "signal": 0, "classified": 0, "alerted": 0}
    max_ts = since
    llm_calls = 0

    for art in sorted(articles, key=lambda a: a.published_at):
        max_ts = max(max_ts, art.published_at)
        wl_tickers = [t for t in art.tickers if t in wl]
        if not wl_tickers:
            continue
        stats["watchlist"] += 1
        if seen.seen(art.headline, wl_tickers):
            continue
        stats["new"] += 1
        seen.add(art.headline, wl_tickers)

        verdict, why = classify_text(art.headline, art.summary)
        if verdict == "noise" or (verdict == "unmatched" and cfg.unmatched_policy == "drop"):
            log.debug("prefilter drop (%s): %s", verdict, art.headline[:90])
            continue
        stats["signal"] += 1

        if llm_calls >= cfg.max_llm_calls_per_run:
            log.warning("LLM call cap (%d) hit; deferring: %s", cfg.max_llm_calls_per_run, art.headline[:90])
            continue
        llm_calls += 1
        try:
            assessments = classify(art, wl_tickers[: cfg.max_tickers_per_article], cfg)
        except Exception:
            log.exception("classifier failed (fail-closed): %s", art.headline[:90])
            continue
        stats["classified"] += 1

        for a in assessments:
            if not passes_gate(a, cfg):
                log.info("gated: %s material=%s conf=%.2f | %s",
                         a.ticker, a.material, a.confidence, art.headline[:90])
                continue
            alert = Alert(article=art, assessment=a)
            if cfg.dry_run:
                log.info("DRY RUN alert: %s %s %.0f%% [%s] %s",
                         a.ticker, a.direction, a.confidence * 100, a.category, art.headline[:120])
            else:
                post_alert(cfg.discord_webhook_url, alert)
                append_alert(cfg.alerts_csv, alert)
            stats["alerted"] += 1

    if not cfg.dry_run:
        seen.save()
        set_watermark(cfg.watermark_file, max_ts)
    log.info("run summary: %s (llm_calls=%d)", stats, llm_calls)
    return 0


if __name__ == "__main__":
    sys.exit(run())
