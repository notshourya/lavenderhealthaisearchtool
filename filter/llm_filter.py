"""
Two-stage LLM filter for insurance complaint causality.

Stage 1 — Per-review classification
  classify_review() asks who is primarily responsible for the complaint.
  Returns INSURER | CLINIC | SHARED | NO + confidence + reasoning.

Stage 2 — Clinic-level aggregation
  analyze_clinic() asks whether the clinic is being unfairly harmed in
  public reviews by insurer-driven insurance friction.

Both stages use gemini-2.5-flash.
"""

from dataclasses import dataclass
from enum import Enum
import re
import time

from google import genai
from google.genai import types

import config

_client = genai.Client(api_key=config.GEMINI_API_KEY)
_REVIEW_BATCH_SIZE = config.LLM_REVIEW_BATCH_SIZE

_REVIEW_SYSTEM = """You are an expert insurance operations analyst reviewing Google reviews for dental clinics.

Your job: determine who is primarily responsible for the insurance-related frustration described in the review.

INSURER:
- the insurer denied the claim because of plan limits, exclusions, waiting periods, or network rules
- the patient is upset about lack of coverage, prior auth issues, reimbursement delays, or EOB confusion
- there is no concrete evidence that the clinic submitted the claim incorrectly or acted deceptively

CLINIC:
- the clinic submitted the wrong billing code
- the clinic promised to file claims and never did
- the clinic double-billed, overcharged, or refused to fix a billing error
- the clinic misrepresented what insurance would cover
- the clinic billed for work not performed or clearly mishandled the claim

SHARED:
- the review is insurance-related but responsibility is mixed or ambiguous
- there may be both insurer friction and clinic communication or process failures

NO:
- the review is not materially about insurance, claims, coverage, reimbursement, or billing responsibility
- it is only a general service complaint

Be conservative. Do not blame the clinic unless the review gives concrete evidence."""

_REVIEW_PROMPT = """Review to classify:
\"\"\"{review_text}\"\"\"

Respond in EXACTLY this format:
VERDICT: INSURER | CLINIC | SHARED | NO
CONFIDENCE: 0.0-1.0
SEVERITY: 1-5
EXPLICIT_INSURANCE_MENTION: YES | NO
REASON: <one concise sentence>"""

CLASSIFICATION_PROMPT = f"{_REVIEW_SYSTEM}\n\n{_REVIEW_PROMPT}"

_BATCH_REVIEW_PROMPT = """Classify each review independently.

Use the same order as the input list.

Reviews:
{review_block}

Return EXACTLY this format for each item:
ITEM 1
VERDICT: INSURER | CLINIC | SHARED | NO
CONFIDENCE: 0.0-1.0
SEVERITY: 1-5
EXPLICIT_INSURANCE_MENTION: YES | NO
REASON: <one concise sentence>

ITEM 2
VERDICT: INSURER | CLINIC | SHARED | NO
CONFIDENCE: 0.0-1.0
SEVERITY: 1-5
EXPLICIT_INSURANCE_MENTION: YES | NO
REASON: <one concise sentence>

..."""

_CLINIC_SYSTEM = """You are assessing whether a dental clinic is being unfairly harmed in public reviews by insurer-driven insurance friction.

You are not looking for fraud by default. You are looking for clinics where patients repeatedly blame the clinic for issues that seem primarily caused by the insurer, plan design, reimbursement delays, or coverage confusion.

Be conservative. Only flag clinics where the evidence shows a meaningful recurring pattern, not one or two isolated complaints."""

_CLINIC_PROMPT = """Clinic: {clinic_name}
Google rating: {rating} / 5.0
Total reviews on Google: {total_reviews}
Reviews primarily caused by insurer friction: {insurer_count} ({complaint_rate:.1f}% of all reviews)
Reviews primarily caused by clinic fault: {clinic_count}
Mixed or unclear insurance complaints: {shared_count}

INSURER-FAULT reviews:
{insurer_text}

CLINIC-FAULT reviews:
{clinic_text}

SHARED/UNCLEAR reviews:
{shared_text}

Determine whether this clinic should be targeted for outreach because it appears to be unfairly harmed by insurer-driven review complaints.

Respond in EXACTLY this format:
VERDICT: YES | NO
CONFIDENCE: 0.0-1.0
SEVERITY: LOW | MEDIUM | HIGH
PATTERN: <one sentence — what the insurer-driven pattern is if YES, or why not a target if NO>"""


class ReviewVerdict(str, Enum):
    INSURER = "INSURER"
    CONFIRMED = "INSURER"
    CLINIC = "CLINIC"
    SHARED = "SHARED"
    UNCERTAIN = "SHARED"
    NO = "NO"


@dataclass
class ReviewClassification:
    verdict: ReviewVerdict
    confidence: float
    reasoning: str
    severity: int = 1
    explicit_insurance_mention: bool = False


LLMVerdict = ReviewClassification


@dataclass
class ClinicVerdict:
    is_target: bool
    confidence: float
    severity: str
    pattern: str


def _generate_content_with_retry(*, contents: str, system_instruction: str, max_attempts: int = 4):
    delay_seconds = 1.0
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            return _client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_instruction),
            )
        except Exception as exc:
            last_error = exc
            error_text = str(exc).lower()
            retryable = any(token in error_text for token in ("429", "toomanyrequests", "resource_exhausted", "quota"))
            if not retryable or attempt == max_attempts:
                raise
            time.sleep(delay_seconds)
            delay_seconds = min(delay_seconds * 2, 8.0)

    if last_error:
        raise last_error
    raise RuntimeError("Gemini request failed")


def classify_review(review_text: str) -> ReviewClassification:
    response = _generate_content_with_retry(
        contents=_REVIEW_PROMPT.format(review_text=review_text),
        system_instruction=_REVIEW_SYSTEM,
    )
    return _parse_review_response(response.text.strip())


def classify_reviews(review_texts: list[str]) -> list[ReviewClassification]:
    if not review_texts:
        return []

    verdicts: list[ReviewClassification] = []
    for start in range(0, len(review_texts), _REVIEW_BATCH_SIZE):
        batch = review_texts[start:start + _REVIEW_BATCH_SIZE]
        if len(batch) == 1:
            verdicts.append(classify_review(batch[0]))
            continue

        review_block = "\n\n".join(f"[{idx + 1}] {text}" for idx, text in enumerate(batch))
        response = _generate_content_with_retry(
            contents=_BATCH_REVIEW_PROMPT.format(review_block=review_block),
            system_instruction=_REVIEW_SYSTEM,
        )
        verdicts.extend(_parse_batch_review_response(response.text.strip(), len(batch)))

    return verdicts


def _parse_review_response(raw: str) -> ReviewClassification:
    verdict = ReviewVerdict.NO
    confidence = 0.0
    reasoning = raw
    severity = 1
    explicit_insurance_mention = False

    verdict_match = re.search(r"VERDICT:\s*(INSURER|CLINIC|SHARED|NO)", raw, re.IGNORECASE)
    confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", raw)
    severity_match = re.search(r"SEVERITY:\s*([1-5])", raw, re.IGNORECASE)
    explicit_match = re.search(r"EXPLICIT_INSURANCE_MENTION:\s*(YES|NO)", raw, re.IGNORECASE)
    reason_match = re.search(r"REASON:\s*(.+)", raw)

    if verdict_match:
        verdict = ReviewVerdict(verdict_match.group(1).upper())
    if confidence_match:
        confidence = min(1.0, max(0.0, float(confidence_match.group(1))))
    if severity_match:
        severity = int(severity_match.group(1))
    if explicit_match:
        explicit_insurance_mention = explicit_match.group(1).upper() == "YES"
    if reason_match:
        reasoning = reason_match.group(1).strip()

    return ReviewClassification(
        verdict=verdict,
        confidence=confidence,
        reasoning=reasoning,
        severity=severity,
        explicit_insurance_mention=explicit_insurance_mention,
    )


def _parse_batch_review_response(raw: str, expected_count: int) -> list[ReviewClassification]:
    blocks = re.split(r"(?=ITEM\s+\d+)", raw, flags=re.IGNORECASE)
    parsed: dict[int, ReviewClassification] = {}
    for block in blocks:
        match = re.search(r"ITEM\s+(\d+)", block, re.IGNORECASE)
        if not match:
            continue
        index = int(match.group(1))
        parsed[index] = _parse_review_response(block)

    if not parsed:
        fallback = _parse_review_response(raw)
        return [fallback for _ in range(expected_count)]

    return [
        parsed.get(index, ReviewClassification(verdict=ReviewVerdict.NO, confidence=0.0, reasoning=raw))
        for index in range(1, expected_count + 1)
    ]


def analyze_clinic(
    clinic_name: str,
    overall_rating: float | None,
    total_reviews: int | None,
    insurer_reviews: list[str],
    clinic_reviews: list[str],
    shared_reviews: list[str],
) -> ClinicVerdict:
    total = total_reviews or max(len(insurer_reviews) + len(clinic_reviews) + len(shared_reviews), 1)
    complaint_rate = (len(insurer_reviews) / total) * 100

    def _fmt(reviews: list[str]) -> str:
        if not reviews:
            return "  (none)"
        return "\n".join(f'  [{i + 1}] "{text[:300]}"' for i, text in enumerate(reviews[:8]))

    prompt = _CLINIC_PROMPT.format(
        clinic_name=clinic_name,
        rating=overall_rating or "unknown",
        total_reviews=total_reviews or "unknown",
        insurer_count=len(insurer_reviews),
        complaint_rate=complaint_rate,
        clinic_count=len(clinic_reviews),
        shared_count=len(shared_reviews),
        insurer_text=_fmt(insurer_reviews),
        clinic_text=_fmt(clinic_reviews),
        shared_text=_fmt(shared_reviews),
    )

    response = _generate_content_with_retry(
        contents=prompt,
        system_instruction=_CLINIC_SYSTEM,
    )
    return _parse_clinic_response(response.text.strip())


def _parse_clinic_response(raw: str) -> ClinicVerdict:
    is_target = False
    confidence = 0.0
    severity = "LOW"
    pattern = raw

    verdict_match = re.search(r"VERDICT:\s*(YES|NO)", raw, re.IGNORECASE)
    confidence_match = re.search(r"CONFIDENCE:\s*([\d.]+)", raw)
    severity_match = re.search(r"SEVERITY:\s*(LOW|MEDIUM|HIGH)", raw, re.IGNORECASE)
    pattern_match = re.search(r"PATTERN:\s*(.+)", raw)

    if verdict_match:
        is_target = verdict_match.group(1).upper() == "YES"
    if confidence_match:
        confidence = min(1.0, max(0.0, float(confidence_match.group(1))))
    if severity_match:
        severity = severity_match.group(1).upper()
    if pattern_match:
        pattern = pattern_match.group(1).strip()

    return ClinicVerdict(
        is_target=is_target,
        confidence=confidence,
        severity=severity,
        pattern=pattern,
    )
