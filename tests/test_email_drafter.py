import pytest
from unittest.mock import MagicMock, patch
from drafter.email_drafter import draft_outreach_email, EmailDraftResult, SYSTEM_PROMPT


def make_mock_response(content: str) -> MagicMock:
    return MagicMock(text=content)


SAMPLE_LLM_OUTPUT = """SUBJECT: A pattern we noticed about Bright Smiles Dental
SUBJECT_ALT_1: Helping Bright Smiles resolve patient insurance complaints
SUBJECT_ALT_2: We noticed something in your reviews, Bright Smiles

BODY:
<p>Hi Jane,</p>

<p>We came across some reviews for Bright Smiles Dental that mentioned challenges with insurance claims — patients expressing frustration about denied claims and unreceived reimbursements.</p>

<p>We help dental practices resolve exactly these types of billing issues faster and with less administrative burden. I'd love to share how we've helped similar practices in Houston.</p>

<p>Would you have 15 minutes this week?</p>

<p>Best,<br>LavenderHealth Team</p>"""


def test_draft_returns_email_draft_result():
    with patch("drafter.email_drafter._model") as mock_model:
        mock_model.generate_content.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Insurance claim denied.", "Reimbursement never came."],
        )
    assert isinstance(result, EmailDraftResult)


def test_draft_extracts_subject():
    with patch("drafter.email_drafter._model") as mock_model:
        mock_model.generate_content.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Claim denied."],
        )
    assert "Bright Smiles" in result.subject


def test_draft_extracts_three_subject_variants():
    with patch("drafter.email_drafter._model") as mock_model:
        mock_model.generate_content.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Claim denied."],
        )
    assert len(result.subject_variants) == 3


def test_draft_body_contains_html():
    with patch("drafter.email_drafter._model") as mock_model:
        mock_model.generate_content.return_value = make_mock_response(SAMPLE_LLM_OUTPUT)
        result = draft_outreach_email(
            clinic_name="Bright Smiles Dental",
            contact_first_name="Jane",
            flagged_review_excerpts=["Claim denied."],
        )
    assert "<p>" in result.body


def test_system_prompt_mentions_lavenderhealth():
    assert "LavenderHealth" in SYSTEM_PROMPT or "lavenderhealth" in SYSTEM_PROMPT.lower()


def test_system_prompt_instructs_empathy():
    assert "empat" in SYSTEM_PROMPT.lower() or "understand" in SYSTEM_PROMPT.lower()
