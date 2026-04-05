from filter.keyword_filter import (
    ReviewScore,
    TIER1,
    TIER2,
    TIER3,
    infer_issue_category,
    qualifies_for_llm,
    score_review,
)
from db.models import IssueCategory


def test_tier1_direct_match():
    result = score_review("They denied my insurance claim without any reason.")
    assert result.tier1_hits > 0
    assert "insurance claim" in result.matched_keywords or "claim denied" in result.matched_keywords


def test_tier2_supporting_match():
    result = score_review("I am still waiting and dealing with a billing issue.")
    assert result.tier2_hits > 0
    assert "billing issue" in result.matched_keywords


def test_tier3_sentiment_only():
    result = score_review("This whole situation feels like a scam.")
    assert result.tier3_hits > 0
    assert result.tier1_hits == 0


def test_no_match():
    result = score_review("Great dentist, very friendly staff and clean office.")
    assert result.tier1_hits == 0
    assert result.tier2_hits == 0
    assert result.tier3_hits == 0
    assert result.matched_keywords == []


def test_qualifies_with_two_strong_reviews():
    reviews = [
        "Insurance claim denied.",
        "My reimbursement is still pending after months.",
        "Great cleaning today.",
    ]
    assert qualifies_for_llm(reviews) is True


def test_does_not_qualify_with_one_isolated_tier1():
    reviews = [
        "Insurance claim denied.",
        "Waited a long time.",
        "Staff was rude.",
    ]
    assert qualifies_for_llm(reviews) is False


def test_qualifies_with_one_strong_and_one_supporting_signal():
    reviews = [
        "Insurance claim denied.",
        "Coverage issue with the visit and I am still waiting.",
        "Good parking.",
    ]
    assert qualifies_for_llm(reviews) is True


def test_case_insensitive_matching():
    result = score_review("INSURANCE CLAIM was rejected by the plan.")
    assert result.tier1_hits > 0


def test_review_score_is_dataclass():
    result = score_review("test")
    assert isinstance(result, ReviewScore)


def test_infer_issue_category_claim_denial():
    assert infer_issue_category("My claim was denied by insurance.") == IssueCategory.CLAIM_DENIAL


def test_infer_issue_category_authorization():
    assert infer_issue_category("Prior authorization was rejected.") == IssueCategory.AUTHORIZATION_ISSUE


def test_keyword_constants_are_non_empty():
    assert TIER1
    assert TIER2
    assert TIER3
