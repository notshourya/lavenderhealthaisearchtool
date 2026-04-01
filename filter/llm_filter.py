from dataclasses import dataclass

import anthropic

import config

anthropic_client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)

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
    response = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=100,
        messages=[
            {
                "role": "user",
                "content": CLASSIFICATION_PROMPT.format(review_text=review_text),
            }
        ],
    )
    raw = response.content[0].text.strip()
    is_yes = raw.upper().startswith("YES")
    reasoning = raw.split(".", 1)[1].strip() if "." in raw else raw
    return LLMVerdict(is_insurance_complaint=is_yes, reasoning=reasoning)


def classify_reviews(review_texts: list[str]) -> list[LLMVerdict]:
    """Classify each review individually. Returns one verdict per input."""
    return [classify_review(text) for text in review_texts]
