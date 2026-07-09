from datetime import date

from newsbot.config import Config
from newsbot.scorecard import _close_before, _close_on_or_after, _correct, evaluate, summarize
from newsbot.storage import ALERT_COLUMNS

CLOSES = {
    date(2026, 7, 1): 100.0,
    date(2026, 7, 2): 103.0,
    date(2026, 7, 6): 97.0,
    date(2026, 7, 10): 105.0,
}


def test_close_helpers():
    assert _close_before(CLOSES, date(2026, 7, 2)) == (date(2026, 7, 1), 100.0)
    assert _close_on_or_after(CLOSES, date(2026, 7, 3)) == (date(2026, 7, 6), 97.0)
    assert _close_on_or_after(CLOSES, date(2026, 7, 11)) == (None, None)


def test_correct_logic():
    assert _correct("up", 2.5, 2.0) == "True"
    assert _correct("up", -1.0, 2.0) == "False"
    assert _correct("down", -0.5, 2.0) == "True"
    assert _correct("unclear", 2.5, 2.0) == "True"
    assert _correct("unclear", 0.4, 2.0) == "False"


def _row(**kw):
    r = {c: "" for c in ALERT_COLUMNS}
    r.update({"id": "abc", "alert_ts": "2026-07-02T14:00:00+00:00", "ticker": "ACME",
              "direction": "up", "confidence": "0.90", "category": "earnings_surprise",
              "headline": "h", "url": "u"})
    r.update(kw)
    return r


def test_evaluate_fills_checkpoints(monkeypatch):
    import newsbot.scorecard as sc
    monkeypatch.setattr(sc, "fetch_closes", lambda t, s, e: CLOSES)
    rows = [_row()]
    n = evaluate(rows, Config(), today=date(2026, 7, 12))
    assert n == 2
    r = rows[0]
    assert r["baseline_close"] == "100.00"           # close before alert date
    assert r["t1d_close"] == "97.00" and r["t1d_correct"] == "False"   # 7/6 close, -3%
    assert r["t1w_close"] == "105.00" and r["t1w_correct"] == "True"   # 7/10 close, +5%
    assert "Scorecard" in summarize(rows)


def test_evaluate_skips_not_yet_due(monkeypatch):
    import newsbot.scorecard as sc
    monkeypatch.setattr(sc, "fetch_closes", lambda t, s, e: CLOSES)
    rows = [_row()]
    evaluate(rows, Config(), today=date(2026, 7, 6))
    assert rows[0]["t1d_correct"] == "False" or rows[0]["t1d_correct"] == "True"
    assert rows[0]["t1w_correct"] == ""  # T+1w not due yet
