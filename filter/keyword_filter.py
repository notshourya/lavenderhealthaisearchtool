"""
Keyword pre-filter — cheap first pass before any LLM calls.

Tier 1: Phrases that almost certainly indicate a clinic-side billing problem.
         A single hit warrants LLM investigation.

Tier 2: Phrases that suggest billing frustration but could be ambiguous.
         Multiple hits across reviews needed to warrant LLM investigation.

Design principle: cast a wide net here (high recall), let the LLM stages
handle precision. But avoid generic words like "billing" alone that fire
on every "billing was easy" review.
"""

from dataclasses import dataclass, field

# Strong signals — almost always clinic-side issues
TIER1: list[str] = [
    "insurance claim",
    "insurance denied",
    "claim denied",
    "claim rejected",
    "claim not processed",
    "claim not submitted",
    "never submitted my claim",
    "failed to submit",
    "didn't submit",
    "explanation of benefits",
    "eob",
    "insurance fraud",
    "billed incorrectly",
    "billed my insurance",
    "wrong billing code",
    "wrong code",
    "upcoding",
    "balance billing",
    "insurance won't pay",
    "insurance didn't pay",
    "insurance hasn't paid",
    "insurance reimbursement",
    "reimbursement",
    "overcharged",
    "double charged",
    "double billed",
    "charged twice",
    "collected from insurance and from me",
    "billed both",
]

# Weaker signals — need multiple hits or combined with tier 1
TIER2: list[str] = [
    "billing issue",
    "billing problem",
    "billing error",
    "billing dispute",
    "charged wrong",
    "wrong amount",
    "unexpected charge",
    "unexpected bill",
    "hidden fee",
    "hidden charge",
    "never paid back",
    "still waiting for refund",
    "won't refund",
    "refused to refund",
    "out of network",
    "out of pocket",
    "charged out of pocket",
]

# Fraud/ethics signals — elevate severity when combined with billing context
TIER3: list[str] = [
    "fraud",
    "scam",
    "theft",
    "stole",
    "dishonest",
    "deceptive",
    "misleading",
    "lied about",
    "false claim",
    "fake claim",
]


@dataclass
class ReviewScore:
    tier1_hits: int = 0
    tier2_hits: int = 0
    tier3_hits: int = 0
    matched_keywords: list[str] = field(default_factory=list)


def score_review(text: str) -> ReviewScore:
    lowered = text.lower()
    score = ReviewScore()

    for phrase in TIER1:
        if phrase in lowered:
            score.tier1_hits += 1
            score.matched_keywords.append(phrase)

    for phrase in TIER2:
        if phrase in lowered:
            score.tier2_hits += 1
            score.matched_keywords.append(phrase)

    for phrase in TIER3:
        if phrase in lowered:
            score.tier3_hits += 1
            score.matched_keywords.append(phrase)

    return score


def qualifies_for_llm(review_texts: list[str]) -> bool:
    """
    Return True if the clinic's reviews as a whole warrant LLM investigation.

    Conservative gate — we want high recall here (don't miss real problems),
    precision comes from the LLM stages that follow.
    """
    tier1_total = 0
    tier2_total = 0
    tier3_total = 0

    for text in review_texts:
        s = score_review(text)
        tier1_total += s.tier1_hits
        tier2_total += s.tier2_hits
        tier3_total += s.tier3_hits

    # Any strong-signal mention warrants LLM review
    if tier1_total >= 1:
        return True

    # Two or more weaker signals combined
    if (tier1_total + tier2_total) >= 2:
        return True

    # Fraud language even without billing keywords — LLM will sort it out
    if tier3_total >= 2:
        return True

    return False
