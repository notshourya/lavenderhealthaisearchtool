from drafter.email_drafter import draft_outreach_email, EmailDraftResult, SYSTEM_PROMPT


def test_draft_returns_email_draft_result():
    result = draft_outreach_email(
        clinic_name="Bright Smiles Dental",
        contact_first_name="Jane",
        flagged_review_excerpts=["Insurance claim denied.", "Reimbursement never came."],
    )
    assert isinstance(result, EmailDraftResult)


def test_draft_extracts_subject():
    result = draft_outreach_email(
        clinic_name="Bright Smiles Dental",
        contact_first_name="Jane",
        flagged_review_excerpts=["Claim denied."],
    )
    assert "Bright Smiles" in result.subject


def test_draft_extracts_three_subject_variants():
    result = draft_outreach_email(
        clinic_name="Bright Smiles Dental",
        contact_first_name="Jane",
        flagged_review_excerpts=["Claim denied."],
    )
    assert len(result.subject_variants) == 3


def test_draft_body_contains_html():
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


def test_draft_uses_review_excerpt_summary():
    result = draft_outreach_email(
        clinic_name="Bright Smiles Dental",
        contact_first_name="Jane",
        flagged_review_excerpts=["Insurance claim denied.", "Reimbursement never came."],
    )
    assert "Insurance claim denied" in result.body
    assert "Reimbursement never came" in result.body
