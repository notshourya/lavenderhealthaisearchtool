"""
Two-stage LLM filter for insurance billing complaints.

Stage 1 — Per-review classification
  classify_review() asks: is this review the CLINIC'S fault?
  Returns CONFIRMED | UNCERTAIN | NO + confidence + reasoning.

  Critical distinction:
  - CONFIRMED: clinic submitted wrong codes, failed to submit, double-billed,
    promised to handle insurance and didn't, billed for procedures not performed
  - UNCERTAIN: billing complaint but unclear who's responsible
  - NO: patient's plan doesn't cover it, or unrelated complaint

Stage 2 — Clinic-level systemic analysis
  analyze_clinic() gets ALL confirmed + uncertain reviews for one clinic
  and asks: is this a SYSTEMIC pattern, not isolated incidents?
  Returns: is_systemic, confidence (0–1), pattern summary, severity.

Both stages use gemini-2.5-flash (fast, low cost, high accuracy).
"""

from dataclasses import dataclass
from enum import Enum

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)

# ── Per-review prompt ─────────────────────────────────────────────────────────

_REVIEW_SYSTEM = """You are an expert insurance billing auditor reviewing patient Google reviews for dental clinics.

Your job: determine whether the complaint in a review is the DENTAL CLINIC'S FAULT, not the patient's insurance plan.

CONFIRMED (clinic is responsible):
- Clinic submitted wrong billing codes → insurance denied
- Clinic promised to submit claims and never did
- Clinic billed for procedures never performed
- Clinic double-billed patient and/or insurance
- Clinic refused to correct a billing error or resubmit a claim
- Clinic collected copay AND full payment, or billed more than the contracted rate
- Clinic misrepresented what insurance would cover before treatment

NOT the clinic's fault (answer NO):
- Patient's plan simply doesn't cover the procedure
- Patient didn't understand their own coverage limits
- Insurance company took a long time to pay (no evidence clinic acted badly)
- Patient upset about cost but no specific billing error alleged

UNCERTAIN when:
- There's clearly a billing dispute but it's genuinely ambiguous who caused it
- Review is vague and could go either way"""

_REVIEW_PROMPT = """Review to classify:
\"\"\"{review_text}\"\"\"

Respond on a single line in EXACTLY this format (no other text):
VERDICT: CONFIRMED | UNCERTAIN | NO
CONFIDENCE: 0.0-1.0
REASON: <one concise sentence>"""

# ── Clinic-level prompt ───────────────────────────────────────────────────────

_CLINIC_SYSTEM = """You are an insurance billing fraud investigator assessing whether a dental clinic has a SYSTEMIC billing problem affecting multiple patients.

A systemic problem means the clinic routinely (not accidentally) engages in billing misconduct: wrong codes, failure to submit, fraudulent charges, or deliberate overcharging. This is different from one or two isolated administrative errors any busy practice might make.

Be conservative. Only flag clinics where the evidence strongly suggests an ongoing pattern, not a few unlucky patients."""

_CLINIC_PROMPT = """Clinic: {clinic_name}
Google rating: {rating} / 5.0
Total reviews on Google: {total_reviews}
Reviews with confirmed insurance complaints: {confirmed_count} ({complaint_rate:.1f}% of all reviews)
Reviews with uncertain insurance complaints: {uncertain_count}

CONFIRMED complaint reviews (clinic clearly at fault):
{confirmed_text}

UNCERTAIN complaint reviews (may or may not be clinic's fault):
{uncertain_text}

Determine whether this clinic has a SYSTEMIC insurance billing problem.

Ask yourself:
1. Do multiple independent reviewers describe the SAME specific misconduct?
2. Are the complaints specific and credible (mention amounts, claim numbers, specific errors)?
3. Given the total review count, is this complaint rate meaningful or statistical noise?
4. Does the pattern suggest intentional misconduct vs occasional administrative mistakes?

Respond in EXACTLY this format (no other text):
VERDICT: YES | NO
CONFIDENCE: 0.0-1.0
SEVERITY: LOW | MEDIUM | HIGH
PATTERN: <one sentence — what the pattern is if YES, or why not systemic if NO>"""


# ── Data classes ──────────────────────────────────────────────────────────────

class ReviewVerdict(str, Enum):
    CONFIRMED = "CONFIRMED"
    UNCERTAIN = "UNCERTAIN"
    NO = "NO"


@dataclass
class ReviewClassification:
    verdict: ReviewVerdict
    confidence: float
    reasoning: str


@dataclass
class ClinicVerdict:
    is_systemic: bool
    confidence: float       # 0.0–1.0
    severity: str           # LOW | MEDIUM | HIGH
    pattern: str            # human-readable summary


# ── Stage 1: per-review ───────────────────────────────────────────────────────

def classify_review(review_text: str) -> ReviewClassification:
    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=_REVIEW_PROMPT.format(review_text=review_text),
        config=types.GenerateContentConfig(system_instruction=_REVIEW_SYSTEM),
    )
    return _parse_review_response(response.text.strip())


def classify_reviews(review_texts: list[str]) -> list[ReviewClassification]:
    return [classify_review(t) for t in review_texts]


def _parse_review_response(raw: str) -> ReviewClassification:
    import re
    verdict = ReviewVerdict.NO
    confidence = 0.0
    reasoning = raw

    v_match = re.search(r"VERDICT:\s*(CONFIRMED|UNCERTAIN|NO)", raw, re.IGNORECASE)
    c_match = re.search(r"CONFIDENCE:\s*([\d.]+)", raw)
    r_match = re.search(r"REASON:\s*(.+)", raw)

    if v_match:
        verdict = ReviewVerdict(v_match.group(1).upper())
    if c_match:
        confidence = min(1.0, max(0.0, float(c_match.group(1))))
    if r_match:
        reasoning = r_match.group(1).strip()

    return ReviewClassification(verdict=verdict, confidence=confidence, reasoning=reasoning)


# ── Stage 2: clinic-level ─────────────────────────────────────────────────────

def analyze_clinic(
    clinic_name: str,
    overall_rating: float | None,
    total_reviews: int | None,
    confirmed_reviews: list[str],
    uncertain_reviews: list[str],
) -> ClinicVerdict:
    total = total_reviews or max(len(confirmed_reviews) + len(uncertain_reviews), 1)
    complaint_rate = (len(confirmed_reviews) / total) * 100

    def _fmt(reviews: list[str]) -> str:
        if not reviews:
            return "  (none)"
        return "\n".join(f'  [{i+1}] "{t[:300]}"' for i, t in enumerate(reviews[:8]))

    prompt = _CLINIC_PROMPT.format(
        clinic_name=clinic_name,
        rating=overall_rating or "unknown",
        total_reviews=total_reviews or "unknown",
        confirmed_count=len(confirmed_reviews),
        complaint_rate=complaint_rate,
        uncertain_count=len(uncertain_reviews),
        confirmed_text=_fmt(confirmed_reviews),
        uncertain_text=_fmt(uncertain_reviews),
    )

    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(system_instruction=_CLINIC_SYSTEM),
    )
    return _parse_clinic_response(response.text.strip())


def _parse_clinic_response(raw: str) -> ClinicVerdict:
    import re
    is_systemic = False
    confidence = 0.0
    severity = "LOW"
    pattern = raw

    v_match = re.search(r"VERDICT:\s*(YES|NO)", raw, re.IGNORECASE)
    c_match = re.search(r"CONFIDENCE:\s*([\d.]+)", raw)
    s_match = re.search(r"SEVERITY:\s*(LOW|MEDIUM|HIGH)", raw, re.IGNORECASE)
    p_match = re.search(r"PATTERN:\s*(.+)", raw)

    if v_match:
        is_systemic = v_match.group(1).upper() == "YES"
    if c_match:
        confidence = min(1.0, max(0.0, float(c_match.group(1))))
    if s_match:
        severity = s_match.group(1).upper()
    if p_match:
        pattern = p_match.group(1).strip()

    return ClinicVerdict(
        is_systemic=is_systemic,
        confidence=confidence,
        severity=severity,
        pattern=pattern,
    )
