import pytest
from unittest.mock import MagicMock, patch
from filter.llm_filter import classify_reviews, LLMVerdict, CLASSIFICATION_PROMPT


def make_mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_classify_yes_response():
    with patch("filter.llm_filter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(
            "YES. The reviewer explicitly states their insurance claim was denied and they were charged out of pocket."
        )
        verdicts = classify_reviews(["They denied my insurance claim and I had to pay $500 out of pocket."])

    assert len(verdicts) == 1
    assert verdicts[0].is_insurance_complaint is True
    assert verdicts[0].reasoning != ""


def test_classify_no_response():
    with patch("filter.llm_filter.anthropic_client") as mock_client:
        mock_client.messages.create.return_value = make_mock_response(
            "NO. The reviewer mentions waiting time and staff attitude but nothing about insurance claims."
        )
        verdicts = classify_reviews(["The wait was too long and the staff seemed rude."])

    assert len(verdicts) == 1
    assert verdicts[0].is_insurance_complaint is False


def test_classify_batch_of_reviews():
    responses = [
        "YES. Clear insurance billing complaint.",
        "NO. General service complaint.",
        "YES. Mentions denied reimbursement.",
    ]
    call_count = 0

    def side_effect(**kwargs):
        nonlocal call_count
        resp = make_mock_response(responses[call_count])
        call_count += 1
        return resp

    with patch("filter.llm_filter.anthropic_client") as mock_client:
        mock_client.messages.create.side_effect = side_effect
        verdicts = classify_reviews([
            "They denied my insurance claim.",
            "The wait was terrible.",
            "Reimbursement was never processed.",
        ])

    assert len(verdicts) == 3
    assert verdicts[0].is_insurance_complaint is True
    assert verdicts[1].is_insurance_complaint is False
    assert verdicts[2].is_insurance_complaint is True


def test_llm_verdict_is_dataclass():
    verdict = LLMVerdict(is_insurance_complaint=True, reasoning="Test")
    assert verdict.is_insurance_complaint is True
    assert verdict.reasoning == "Test"


def test_classification_prompt_contains_dental_context():
    assert "dental" in CLASSIFICATION_PROMPT.lower()
    assert "insurance" in CLASSIFICATION_PROMPT.lower()
    assert "YES" in CLASSIFICATION_PROMPT
    assert "NO" in CLASSIFICATION_PROMPT
