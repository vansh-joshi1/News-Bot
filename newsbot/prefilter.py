"""Rule-based pre-filter: cheap regexes that decide whether a headline earns an LLM call.

Three outcomes:
  "signal"    — matches a materiality category; send to the LLM.
  "noise"     — matches a known-junk pattern (and no signal); drop.
  "unmatched" — matches neither; config.unmatched_policy decides (default: drop).

The signal list is deliberately generous (the LLM is the real judge); the noise
list is deliberately conservative (a wrong drop here is unrecoverable).
"""
import re

_S = [
    # (category, pattern) — checked case-insensitively against headline + summary
    ("earnings", r"\b(beats?|misses?|tops?|falls? short of|exceeds?)\b.{0,40}\b(estimates?|expectations|consensus|forecasts?)\b"),
    ("earnings", r"\b(q[1-4]|quarterly|full[- ]year)\b.{0,50}\b(results|earnings|revenue|eps)\b"),
    ("earnings", r"\bearnings\b.{0,30}\b(surprise|beat|miss)\b"),
    ("ma", r"\b(acquir\w+|merger|merges?|buyout|takeover|take[- ]private|divest\w+|spin[- ]?off|to buy|to sell .{0,30}(unit|division|business))\b"),
    ("ma", r"\b(bid for|offer to acquire|acquisition of|deal to (buy|acquire|merge))\b"),
    ("analyst", r"\b(upgrades?d?|downgrades?d?)\b"),
    ("analyst", r"\bprice target\b|\bpt (raised|cut|lowered|hiked)\b"),
    ("regulatory", r"\bfda\b.{0,60}\b(approv\w+|reject\w+|complete response|clearance|clinical hold|fast track|breakthrough)\b"),
    ("regulatory", r"\b(antitrust|doj|ftc|sec charges?|probe|investigation|subpoena)\b"),
    ("legal", r"\b(lawsuit|sues?d?|settl\w+|verdict|injunction|class action)\b"),
    ("guidance", r"\b(guidance|outlook|forecast)\b.{0,40}\b(raise[sd]?|cut[s]?|lower\w*|boost\w*|withdraw\w*|hike[sd]?|slash\w*|updat\w+)\b"),
    ("guidance", r"\b(raises?|cuts?|lowers?|withdraws?)\b.{0,30}\b(guidance|outlook|forecast)\b"),
    ("exec", r"\b(ceo|cfo|chief executive|chief financial)\b.{0,60}\b(resign\w*|steps? down|depart\w*|exits?|fired|ousted|retir\w+|appoint\w+|names?|hires?|succeed\w*|interim)\b"),
    ("exec", r"\b(appoints?|names?)\b.{0,40}\b(ceo|cfo|chief executive|chief financial)\b"),
    ("contract", r"\b(wins?|awarded|loses?|cancels?)\b.{0,50}\b(contract|order|deal)\b.{0,60}(\$|million|billion)"),
    ("contract", r"\$\d+(\.\d+)?\s?(billion|bn|b)\b.{0,40}\b(contract|order|deal|agreement)\b"),
    ("insider", r"\b(form 4|insider (buy\w*|sell\w*|purchas\w+)|(ceo|cfo|director|officer) (buys?|sells?|purchases?)\b.{0,40}(shares|stock))"),
    ("credit", r"\b(moody'?s|s&p global ratings|fitch)\b.{0,60}\b(upgrade\w*|downgrade\w*|rating|watch|outlook)\b"),
    ("distress", r"\b(bankruptcy|chapter 11|default\w*|going concern|delist\w*|restat\w+ (earnings|results|financials))\b"),
    ("shock", r"\b(recall\w*|halt\w*|explosion|breach|hack\w*|cyberattack|outage)\b"),
    ("squeeze", r"\b(short squeeze|short interest|unusual options)\b"),
]
SIGNAL_PATTERNS = [(c, re.compile(p, re.IGNORECASE)) for c, p in _S]

# Hard noise: checked BEFORE signal rules. Law-firm "shareholder alert" spam
# deliberately name-drops "class action"/"investigation" and would otherwise
# trip the legal signal patterns dozens of times a day.
_HN = [
    r"\b(shareholder|investor) alert\b",
    r"\blaw (firm|offices?)\b.{0,80}\b(class action|investigat\w+|remind\w+|deadline)\b",
    r"\bclass action (reminder|deadline)\b",
    r"\b(rosen|pomerantz|glancy|bronstein|kahn swick|levi & korsinsky|schall)\b.{0,40}\b(law|reminds?)\b",
]
HARD_NOISE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _HN]

_N = [
    r"\bto (present|participate|speak|attend|webcast|host a (fireside|webinar))\b",
    r"\b(fireside chat|investor (conference|day)|analyst day)\b",
    r"\b(named|recognized|honored) (as )?(a |an )?(leader|winner|top|best)\b",
    r"\b(award|awards ceremony|anniversary|celebrates|milestone of)\b",
    r"\bto (announce|report|release) .{0,30}(results|earnings)\b",  # scheduling PR, not the results
    r"\b(conference call|earnings call) (scheduled|to discuss)\b",
    r"\b(appoints?|names?|promotes?)\b.{0,50}\b(vice president|vp|senior director|general manager|head of)\b",
    r"\b(thought leadership|whitepaper|blog post|podcast)\b",
    r"\bdeclares? .{0,20}dividend\b",  # in-line declarations; raises get caught by guidance rules
    r"\b(shareholder alert|investor alert|law (firm|offices?) (of|announc\w+)|class action reminder|deadline (alert|reminder))\b",
]
NOISE_PATTERNS = [re.compile(p, re.IGNORECASE) for p in _N]


def classify_text(headline: str, summary: str = "") -> tuple:
    """Return ("signal", category) | ("noise", pattern) | ("unmatched", "")."""
    text = f"{headline} {summary or ''}"
    for rx in HARD_NOISE_PATTERNS:
        if rx.search(text):
            return ("noise", rx.pattern)
    for category, rx in SIGNAL_PATTERNS:
        if rx.search(text):
            return ("signal", category)
    for rx in NOISE_PATTERNS:
        if rx.search(text):
            return ("noise", rx.pattern)
    return ("unmatched", "")
