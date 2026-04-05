from unittest.mock import MagicMock, patch

from filter.llm_filter import (
    CLASSIFICATION_PROMPT,
    ReviewClassification,
    ReviewVerdict,
    classify_reviews,
)


def make_mock_response(text: str):
    return MagicMock(text=text)


def test_classify_insurer_response():
    with patch("filter.llm_filter._client") as mock_client:
        mock_client.models.generate_content.return_value = make_mock_response(
            "VERDICT: INSURER\nCONFIDENCE: 0.91\nSEVERITY: 4\nEXPLICIT_INSURANCE_MENTION: YES\nREASON: The review blames denial and coverage limits rather than clinic misconduct."
        )
        verdicts = classify_reviews(
            ["My insurance denied the claim and I got stuck paying out of pocket."]
        )

    assert len(verdicts) == 1
    assert verdicts[0].verdict == ReviewVerdict.INSURER
    assert verdicts[0].reasoning != ""
    assert verdicts[0].severity == 4
    assert verdicts[0].explicit_insurance_mention is True


def test_classify_no_response():
    with patch("filter.llm_filter._client") as mock_client:
        mock_client.models.generate_content.return_value = make_mock_response(
            "VERDICT: NO\nCONFIDENCE: 0.88\nSEVERITY: 1\nEXPLICIT_INSURANCE_MENTION: NO\nREASON: The review is about wait time and staff attitude, not insurance."
        )
        verdicts = classify_reviews(["The wait was too long and the staff seemed rude."])

    assert len(verdicts) == 1
    assert verdicts[0].verdict == ReviewVerdict.NO
    assert verdicts[0].explicit_insurance_mention is False


def test_classify_batch_of_reviews():
    batch_response = (
        "ITEM 1\nVERDICT: INSURER\nCONFIDENCE: 0.95\nSEVERITY: 5\nEXPLICIT_INSURANCE_MENTION: YES\nREASON: Coverage denial appears insurer-driven.\n\n"
        "ITEM 2\nVERDICT: NO\nCONFIDENCE: 0.92\nSEVERITY: 1\nEXPLICIT_INSURANCE_MENTION: NO\nREASON: General service complaint.\n\n"
        "ITEM 3\nVERDICT: CLINIC\nCONFIDENCE: 0.80\nSEVERITY: 3\nEXPLICIT_INSURANCE_MENTION: YES\nREASON: The clinic is accused of submitting claims incorrectly."
    )

    with patch("filter.llm_filter._client") as mock_client:
        mock_client.models.generate_content.return_value = make_mock_response(batch_response)
        verdicts = classify_reviews([
            "They said my insurance denied it.",
            "The wait was terrible.",
            "They billed the wrong code to my insurer.",
        ])

    assert len(verdicts) == 3
    assert verdicts[0].verdict == ReviewVerdict.INSURER
    assert verdicts[1].verdict == ReviewVerdict.NO
    assert verdicts[2].verdict == ReviewVerdict.CLINIC
    assert verdicts[0].severity == 5
    assert verdicts[2].explicit_insurance_mention is True
    assert mock_client.models.generate_content.call_count == 1


def test_review_classification_is_dataclass():
    verdict = ReviewClassification(
        verdict=ReviewVerdict.SHARED,
        confidence=0.72,
        reasoning="Mixed signals.",
    )
    assert verdict.verdict == ReviewVerdict.SHARED
    assert verdict.confidence == 0.72


def test_classification_prompt_contains_dental_context():
    assert "dental" in CLASSIFICATION_PROMPT.lower()
    assert "insurance" in CLASSIFICATION_PROMPT.lower()
    assert "INSURER" in CLASSIFICATION_PROMPT
    assert "CLINIC" in CLASSIFICATION_PROMPT
