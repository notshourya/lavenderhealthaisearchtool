from dataclasses import dataclass, field

TIER1: list[str] = [
    "insurance claim",
    "insurance denied",
    "claim rejected",
    "claim not processed",
    "reimbursement",
    "eob",
    "explanation of benefits",
    "out of pocket",
    "overcharged",
    "insurance fraud",
    "billed incorrectly",
    "insurance won't pay",
    "insurance didn't pay",
]

TIER2: list[str] = [
    "never paid",
    "still waiting",
    "where is my money",
    "billing issue",
    "charged wrong",
    "double charged",
    "won't submit",
    "didn't file",
    "insurance won't cover",
    "balance billing",
    "unexpected charge",
    "hidden fee",
    "wrong amount",
]

TIER3: list[str] = [
    "scam",
    "dishonest",
    "deceptive",
    "misleading",
    "stole",
    "theft",
    "fraud",
    "lie",
    "lied",
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
    """Return True if this clinic's reviews warrant LLM analysis."""
    tier1_total = 0
    tier2_total = 0

    for text in review_texts:
        s = score_review(text)
        tier1_total += s.tier1_hits
        tier2_total += s.tier2_hits

    if tier1_total >= 1:
        return True
    if (tier1_total + tier2_total) >= 2:
        return True
    return False
