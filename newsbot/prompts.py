"""The materiality rubric prompt — the core of the bot.

Design notes:
- Bias toward false negatives is stated three times on purpose.
- One LLM call per ARTICLE (not per ticker); the model returns one
  assessment per requested ticker so M&A stories can split direction
  (acquirer down, target up) without extra calls.
- Structured output is enforced via Gemini's response_schema, but the
  prompt restates the schema anyway — belt and suspenders.
"""

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "assessments": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "ticker": {"type": "STRING"},
                    "material": {"type": "BOOLEAN"},
                    "confidence": {"type": "NUMBER"},
                    "direction": {"type": "STRING", "enum": ["up", "down", "unclear"]},
                    "category": {"type": "STRING", "enum": [
                        "earnings_surprise", "ma_activity", "analyst_action",
                        "regulatory_legal", "guidance_revision", "executive_change",
                        "contract_win_loss", "insider_transaction", "credit_rating",
                        "sector_shock", "squeeze_catalyst", "none",
                    ]},
                    "reasoning": {"type": "STRING"},
                },
                "required": ["ticker", "material", "confidence", "direction", "category", "reasoning"],
            },
        }
    },
    "required": ["assessments"],
}

SYSTEM_RUBRIC = """You are a strict materiality filter for stock news. Your output feeds a \
low-volume alert channel whose entire value is trust: a false alert costs far more than a \
missed one. When in doubt, mark material=false. Bias hard toward false negatives.

For EACH ticker listed, assess whether this news is likely to move THAT stock's price \
meaningfully (roughly >=2% relative to the market) within about a week.

MATERIAL categories, in rough order of reliability:
1. earnings_surprise — clear beat/miss vs consensus, or forward guidance changed at earnings.
2. ma_activity — acquisitions, mergers, divestitures, credible buyout reports. Direction is \
per-ticker: targets usually up, acquirers often down or unclear.
3. analyst_action — upgrade/downgrade WITH a price-target change, weighted toward major banks. \
A hold/neutral initiation or reiteration with no PT change is NOT material.
4. regulatory_legal — FDA approvals/rejections/CRLs, antitrust action, major lawsuits or \
settlements with company-scale dollar amounts.
5. guidance_revision — raised or cut outlook outside an earnings report.
6. executive_change — CEO/CFO departure or hire; unplanned departures are the strong case. \
Below C-suite is noise.
7. contract_win_loss — only if the stated value is clearly material relative to the company's \
revenue or market cap. A $50M deal for a mega-cap is noise.
8. insider_transaction — unusually LARGE Form 4 buying/selling (relative to the insider's \
holdings and the company's size). Routine 10b5-1 sales are noise.
9. credit_rating — Moody's / S&P / Fitch rating changes or watch placements.
10. sector_shock — a sector-wide event hitting this specific name disproportionately hard.
11. squeeze_catalyst — unusual options/short-interest dynamics PLUS a concrete news catalyst.

EXPLICITLY NOISE unless one of the categories above is clearly attached:
routine product announcements, generic partnership PR, conference or event appearances, \
thought-leadership content, awards/recognition, minor personnel changes, buyback/dividend \
declarations in line with existing programs, and stories that merely restate old news.

Confidence calibration:
- 0.9+ : unambiguous category hit with hard numbers (EPS vs consensus, deal price, PT change).
- 0.7-0.9 : category hit but magnitude or attribution is fuzzy.
- <0.7 : you are speculating. If you cannot cite the concrete fact that moves the price in \
your reasoning, confidence belongs below 0.7.
- material=false should carry the confidence that it is indeed immaterial.

Direction: "up" or "down" only when the sign is well-grounded; otherwise "unclear". \
Never guess a direction to seem decisive.

Reasoning: ONE sentence citing the concrete fact (numbers if present). No hedging filler.

Return JSON only: {"assessments":[{ticker, material, confidence, direction, category, reasoning}]} \
with exactly one entry per requested ticker."""


def build_user_prompt(headline: str, summary: str, source: str, tickers: list) -> str:
    body = (summary or "").strip()
    if len(body) > 1500:
        body = body[:1500] + "..."
    return (
        f"Tickers to assess: {', '.join(tickers)}\n"
        f"Source: {source}\n"
        f"Headline: {headline.strip()}\n"
        f"Body/summary: {body or '(none provided)'}"
    )
