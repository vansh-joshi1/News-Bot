import json

from newsbot.classifier import parse_response, passes_gate
from newsbot.config import Config
from newsbot.models import Assessment


def _cfg(threshold=0.85):
    c = Config()
    c.confidence_threshold = threshold
    return c


def test_parse_valid_response():
    text = json.dumps({"assessments": [{
        "ticker": "acme", "material": True, "confidence": 0.92,
        "direction": "up", "category": "earnings_surprise", "reasoning": "EPS $2.10 vs $1.80 consensus",
    }]})
    (a,) = parse_response(text, ["ACME"])
    assert a.ticker == "ACME" and a.material and a.confidence == 0.92 and a.direction == "up"


def test_parse_fails_closed_on_garbage():
    (a,) = parse_response("not json at all", ["ACME"])
    assert not a.material and a.confidence == 0.0


def test_parse_fails_closed_on_missing_ticker():
    text = json.dumps({"assessments": [{"ticker": "OTHER", "material": True, "confidence": 0.9,
                                        "direction": "up", "category": "ma_activity", "reasoning": "x"}]})
    (a,) = parse_response(text, ["ACME"])
    assert a.ticker == "ACME" and not a.material


def test_confidence_clamped_and_direction_sanitized():
    text = json.dumps({"assessments": [{"ticker": "ACME", "material": True, "confidence": 1.7,
                                        "direction": "sideways", "category": "none", "reasoning": "x"}]})
    (a,) = parse_response(text, ["ACME"])
    assert a.confidence == 1.0 and a.direction == "unclear"


def test_gate_requires_material_and_confidence():
    cfg = _cfg(0.85)
    mk = lambda m, c: Assessment("ACME", m, c, "up", "earnings_surprise", "x")
    assert passes_gate(mk(True, 0.90), cfg)
    assert passes_gate(mk(True, 0.85), cfg)
    assert not passes_gate(mk(True, 0.84), cfg)
    assert not passes_gate(mk(False, 0.99), cfg)
