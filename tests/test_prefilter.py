from newsbot.prefilter import classify_text

SIGNAL_CASES = [
    "Acme Corp beats Q3 estimates, raises full-year guidance",
    "MegaBank upgrades Acme to Buy, price target lifted to $250",
    "Acme to acquire Widget Inc. in $4.2 billion deal",
    "FDA approves Acme's experimental heart drug",
    "Acme CFO steps down effective immediately",
    "Moody's downgrades Acme credit rating to Baa3",
    "Acme wins $2.1 billion defense contract from Pentagon",
    "Acme cuts 2026 outlook citing weak demand",
    "Acme files for Chapter 11 bankruptcy protection",
    "Acme recalls 2 million vehicles over brake defect",
]

NOISE_CASES = [
    "Acme to present at the Morgan Tech Conference on Tuesday",
    "Acme named a Leader in the 2026 Analyst Quadrant",
    "Acme celebrates 50th anniversary with community event",
    "Acme appoints new Vice President of Marketing",
    "Acme to report third quarter results on October 24",
    "Acme declares quarterly dividend of $0.28 per share",
    "SHAREHOLDER ALERT: Law Offices of Smith announce class action reminder for Acme investors",
]

UNMATCHED_CASES = [
    "Acme opens new office in Austin",
    "Acme releases sustainability report",
]


def test_signal_cases():
    for h in SIGNAL_CASES:
        verdict, _ = classify_text(h)
        assert verdict == "signal", f"expected signal: {h}"


def test_noise_cases():
    for h in NOISE_CASES:
        verdict, _ = classify_text(h)
        assert verdict == "noise", f"expected noise: {h}"


def test_unmatched_cases():
    for h in UNMATCHED_CASES:
        verdict, _ = classify_text(h)
        assert verdict == "unmatched", f"expected unmatched: {h}"


def test_summary_contributes():
    verdict, _ = classify_text("Acme shares in focus", "The company beat consensus estimates and raised guidance.")
    assert verdict == "signal"
