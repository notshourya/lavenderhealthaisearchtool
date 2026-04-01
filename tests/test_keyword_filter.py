import pytest
from filter.keyword_filter import (
    score_review,
    qualifies_for_llm,
    TIER1, TIER2, TIER3,
    ReviewScore,
)


def test_tier1_direct_match():
    result = score_review("They denied my insurance claim without any reason.")
    assert result.tier1_hits > 0
    assert "insurance claim" in result.matched_keywords or "insurance denied" in result.matched_keywords


def test_tier2_indirect_match():
    result = score_review("I was double charged and they never fixed it.")
    assert result.tier2_hits > 0
    assert "double charged" in result.matched_keywords


def test_tier3_sentiment_only():
    result = score_review("This place is a complete scam.")
    assert result.tier3_hits > 0
    assert result.tier1_hits == 0


def test_no_match():
    result = score_review("Great dentist, very friendly staff and clean office.")
    assert result.tier1_hits == 0
    assert result.tier2_hits == 0
    assert result.tier3_hits == 0
    assert result.matched_keywords == []


def test_qualifies_with_two_tier1():
    reviews = [
        "Insurance claim denied.",
        "They never submitted my reimbursement.",
        "Great cleaning today.",
    ]
    assert qualifies_for_llm(reviews) is True


def test_does_not_qualify_with_one_tier1():
    reviews = [
        "Insurance claim denied.",
        "Waited a long time.",
        "Staff was rude.",
    ]
    assert qualifies_for_llm(reviews) is False


def test_qualifies_with_four_tier1_plus_tier2():
    reviews = [
        "Insurance claim denied.",      # tier1
        "Billing issue with my visit.", # tier2
        "Double charged twice.",        # tier2
        "Never paid me back.",          # tier2
        "Good parking.",
    ]
    assert qualifies_for_llm(reviews) is True


def test_case_insensitive_matching():
    result = score_review("INSURANCE CLAIM was rejected by this office.")
    assert result.tier1_hits > 0


def test_review_score_is_dataclass():
    result = score_review("test")
    assert hasattr(result, "tier1_hits")
    assert hasattr(result, "tier2_hits")
    assert hasattr(result, "tier3_hits")
    assert hasattr(result, "matched_keywords")
