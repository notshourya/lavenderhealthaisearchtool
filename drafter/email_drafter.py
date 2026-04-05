from dataclasses import dataclass
import re


SYSTEM_PROMPT = """You are a professional outreach writer for LavenderHealth, a company that helps dental practices reduce the operational and reputational impact of insurance friction.

Your tone is empathetic, professional, and non-accusatory. You acknowledge patient frustration without implying the clinic caused the underlying issue. Your goal is to open a conversation, not make a hard sell.

Write emails that feel personal and specific — reference the clinic by name, use the contact's first name, and briefly acknowledge the pattern you noticed. Keep it concise (under 150 words for the body)."""


@dataclass
class EmailDraftResult:
    subject: str
    subject_variants: list[str]
    body: str


def _clean_excerpt(excerpt: str) -> str:
    return re.sub(r"\s+", " ", excerpt.strip())


def _join_excerpts(flagged_review_excerpts: list[str]) -> str:
    cleaned = [_clean_excerpt(excerpt) for excerpt in flagged_review_excerpts[:3] if excerpt.strip()]
    if not cleaned:
        return "patients appear to be frustrated by insurance-related issues"
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{cleaned[0]}, {cleaned[1]}, and {cleaned[2]}"


def draft_outreach_email(
    clinic_name: str,
    contact_first_name: str | None,
    flagged_review_excerpts: list[str],
) -> EmailDraftResult:
    first_name = contact_first_name or "there"
    excerpt_summary = _join_excerpts(flagged_review_excerpts)

    subject = f"Helping {clinic_name} with insurance friction"
    subject_alt_1 = f"A few review patterns we noticed at {clinic_name}"
    subject_alt_2 = f"Question about patient insurance complaints at {clinic_name}"

    body = (
        f"<p>Hi {first_name},</p>"
        f"<p>We noticed a pattern in public reviews for {clinic_name} around insurance-related frustration, including {excerpt_summary}. It looks like patients may be blaming the clinic for coverage or reimbursement issues that are often hard to untangle.</p>"
        f"<p>LavenderHealth helps dental teams reduce the operational and reputational burden of these situations. If useful, we can share a simple workflow for identifying and responding to these complaints more effectively.</p>"
        f"<p>Would you be open to a quick conversation this week?</p>"
        f"<p>Best,<br>LavenderHealth Team</p>"
    )

    return EmailDraftResult(
        subject=subject,
        subject_variants=[subject, subject_alt_1, subject_alt_2],
        body=body,
    )