from newsbot.dedup import SeenStore, normalize


def make_store(tmp_path):
    return SeenStore(tmp_path / "seen.jsonl", window_hours=48, fuzzy_threshold=0.90)


def test_normalize_strips_source_suffix():
    assert normalize("Acme beats estimates - Reuters") == normalize("Acme beats estimates")


def test_exact_dedup(tmp_path):
    s = make_store(tmp_path)
    s.add("Acme beats Q3 estimates", ["ACME"])
    assert s.seen("Acme beats Q3 estimates", ["ACME"])
    assert s.seen("Acme Beats Q3 Estimates!", ["ACME"])  # case/punct-insensitive


def test_fuzzy_dedup_same_ticker(tmp_path):
    s = make_store(tmp_path)
    s.add("Acme Corp beats third quarter earnings estimates", ["ACME"])
    assert s.seen("Acme Corp beats third-quarter earnings estimates.", ["ACME"])


def test_different_ticker_not_deduped(tmp_path):
    s = make_store(tmp_path)
    s.add("Acme Corp beats third quarter earnings estimates", ["ACME"])
    assert not s.seen("Acme Corp beats third quarter earnings estimates", ["OTHR"])


def test_different_story_not_deduped(tmp_path):
    s = make_store(tmp_path)
    s.add("Acme beats Q3 estimates", ["ACME"])
    assert not s.seen("Acme CFO resigns effective immediately", ["ACME"])


def test_persistence_roundtrip(tmp_path):
    s = make_store(tmp_path)
    s.add("Acme beats Q3 estimates", ["ACME"])
    s.save()
    s2 = make_store(tmp_path)
    assert s2.seen("Acme beats Q3 estimates", ["ACME"])
