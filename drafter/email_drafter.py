import re
from dataclasses import dataclass, field

import anthropic

import config

anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

SYSTEM_PROMPT = """You are a professional outreach writer for LavenderHealth, a company that helps dental practices resolve insurance billing issues and improve their revenue cycle management.

Your tone is empathetic, professional, and non-accusatory. You acknowledge patient frustration without sensationalizing it. Your goal is to open a conversation, not make a hard sell.

Write emails that feel personal and specific — reference the clinic by name, use the contact's first name, and briefly acknowledge the pattern you noticed. Keep it concise (under 150 words for the body)."""

EMAIL_PROMPT = """Write a cold outreach email to a dental clinic whose online reviews show a pattern of insurance claim complaints.

Clinic: {clinic_name}
Contact first name: {contact_first_name}
Flagged review excerpts (anonymized):
{review_excerpts}

Format your response EXACTLY as:
SUBJECT: <primary subject line>
SUBJECT_ALT_1: <alternative subject line 1>
SUBJECT_ALT_2: <alternative subject line 2>

BODY:
<email body in HTML with <p> tags>"""


@dataclass
class EmailDraftResult:
    subject: str
    subject_variants: list[str]
    body: str


def draft_outreach_email(
    clinic_name: str,
    contact_first_name: str | None,
    flagged_review_excerpts: list[str],
) -> EmailDraftResult:
    excerpts_text = "\n".join(f'- "{e}"' for e in flagged_review_excerpts[:3])
    first_name = contact_first_name or "there"

    response = anthropic_client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[
            {
                "role": "user",
                "content": EMAIL_PROMPT.format(
                    clinic_name=clinic_name,
                    contact_first_name=first_name,
                    review_excerpts=excerpts_text,
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()
    return _parse_email_response(raw)


def _parse_email_response(raw: str) -> EmailDraftResult:
    subject_match = re.search(r"^SUBJECT:\s*(.+)$", raw, re.MULTILINE)
    alt1_match = re.search(r"^SUBJECT_ALT_1:\s*(.+)$", raw, re.MULTILINE)
    alt2_match = re.search(r"^SUBJECT_ALT_2:\s*(.+)$", raw, re.MULTILINE)
    body_match = re.search(r"BODY:\s*\n([\s\S]+)$", raw)

    subject = subject_match.group(1).strip() if subject_match else "Following up"
    alt1 = alt1_match.group(1).strip() if alt1_match else subject
    alt2 = alt2_match.group(1).strip() if alt2_match else subject
    body = body_match.group(1).strip() if body_match else raw

    return EmailDraftResult(
        subject=subject,
        subject_variants=[subject, alt1, alt2],
        body=body,
    )
