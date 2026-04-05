"""
Keyword pre-filter for insurance-friction reviews.

The goal here is not to prove clinic fault. It is to cheaply detect reviews
that are likely about insurance, coverage, claim handling, reimbursement, or
billing responsibility so the LLM can decide who is actually at fault.
"""

from dataclasses import dataclass, field

from db.models import IssueCategory


# Strong signals that the review is materially about insurance friction.
TIER1: list[str] = [
    "insurance claim",
    "claim denied",
    "insurance denied",
    "claim rejected",
    "insurance won't cover",
    "insurance didnt cover",
    "insurance didn't cover",
    "out of network",
    "out-of-network",
    "out of pocket",
    "reimbursement",
    "eob",
    "explanation of benefits",
    "prior authorization",
    "pre authorization",
    "pre-auth",
    "not covered",
    "coverage denied",
    "insurance won't pay",
    "insurance didn't pay",
    "insurance hasnt paid",
    "insurance hasn't paid",
]

# Weaker but still relevant context clues.
TIER2: list[str] = [
    "billing issue",
    "billing problem",
    "billing dispute",
    "billing error",
    "coverage",
    "deductible",
    "copay",
    "co-pay",
    "benefits",
    "appeal",
    "authorization",
    "preauth",
    "referred me to insurance",
    "still waiting",
    "never paid back",
    "refund",
]

# Strong negative sentiment that matters only when paired with insurance terms.
TIER3: list[str] = [
    "scam",
    "fraud",
    "dishonest",
    "misleading",
    "lied about",
    "deceptive",
]

_CATEGORY_KEYWORDS: list[tuple[IssueCategory, tuple[str, ...]]] = [
    (
        IssueCategory.CLAIM_DENIAL,
        (
            "claim denied",
            "claim was denied",
            "insurance denied",
            "claim rejected",
            "coverage denied",
            "not covered",
        ),
    ),
    (
        IssueCategory.COVERAGE_CONFUSION,
        (
            "out of network",
            "out-of-network",
            "coverage",
            "benefits",
            "eob",
            "explanation of benefits",
            "deductible",
            "copay",
            "co-pay",
        ),
    ),
    (
        IssueCategory.REIMBURSEMENT_DELAY,
        (
            "reimbursement",
            "still waiting",
            "insurance hasn't paid",
            "insurance didnt pay",
            "insurance didn't pay",
            "insurance won't pay",
            "refund",
            "never paid back",
        ),
    ),
    (
        IssueCategory.AUTHORIZATION_ISSUE,
        (
            "prior authorization",
            "pre authorization",
            "pre-auth",
            "preauth",
            "authorization",
        ),
    ),
    (
        IssueCategory.BILLING_ERROR,
        (
            "billing issue",
            "billing problem",
            "billing dispute",
            "billing error",
            "billed incorrectly",
            "double charged",
            "double billed",
            "charged twice",
        ),
    ),
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

    The gate is broad enough to keep recall high, but not so broad that one
    isolated mention immediately promotes a clinic.
    """
    tier1_reviews = 0
    tier2_reviews = 0
    tier3_reviews = 0

    for text in review_texts:
        score = score_review(text)
        if score.tier1_hits > 0:
            tier1_reviews += 1
        if score.tier2_hits > 0:
            tier2_reviews += 1
        if score.tier3_hits > 0:
            tier3_reviews += 1

    if tier1_reviews >= 2:
        return True

    if tier1_reviews >= 1 and tier2_reviews >= 1:
        return True

    if tier2_reviews >= 3:
        return True

    if tier3_reviews >= 2 and (tier1_reviews + tier2_reviews) >= 1:
        return True

    return False


def infer_issue_category(text: str) -> IssueCategory:
    lowered = text.lower()
    for category, phrases in _CATEGORY_KEYWORDS:
        if any(phrase in lowered for phrase in phrases):
            return category
    return IssueCategory.OTHER
