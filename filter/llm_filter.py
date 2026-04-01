from dataclasses import dataclass

import google.generativeai as genai

import config

genai.configure(api_key=config.GEMINI_API_KEY)
_model = genai.GenerativeModel("gemini-2.0-flash")

CLASSIFICATION_PROMPT = """You are reviewing Google reviews for a dental clinic.

Does the following review describe a problem with insurance claim processing, reimbursement, or billing fraud at a dental clinic?

Answer with exactly: YES or NO, then one sentence explaining why.

Review:
{review_text}"""


@dataclass
class LLMVerdict:
    is_insurance_complaint: bool
    reasoning: str


def classify_review(review_text: str) -> LLMVerdict:
    prompt = CLASSIFICATION_PROMPT.format(review_text=review_text)
    response = _model.generate_content(prompt)
    raw = response.text.strip()
    is_yes = raw.upper().startswith("YES")
    reasoning = raw.split(".", 1)[1].strip() if "." in raw else raw
    return LLMVerdict(is_insurance_complaint=is_yes, reasoning=reasoning)


def classify_reviews(review_texts: list[str]) -> list[LLMVerdict]:
    """Classify each review individually. Returns one verdict per input."""
    return [classify_review(text) for text in review_texts]
