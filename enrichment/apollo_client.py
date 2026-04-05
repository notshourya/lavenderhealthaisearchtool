from dataclasses import dataclass
from urllib.parse import urlparse

import httpx

import config

APOLLO_PEOPLE_URL = "https://api.apollo.io/v1/mixed_people/search"

PRIORITY_TITLES = [
    "office manager",
    "billing coordinator",
    "front desk manager",
    "practice manager",
    "billing manager",
    "insurance coordinator",
    "revenue cycle manager",
]

VALID_EMAIL_STATUSES = {"verified", "likely to engage"}


@dataclass
class ApolloContact:
    email: str
    first_name: str | None
    last_name: str | None
    title: str | None
    confidence_score: float


def _title_priority(title: str | None) -> int:
    """Lower number = higher priority."""
    if not title:
        return 999
    lower = title.lower()
    for idx, priority_title in enumerate(PRIORITY_TITLES):
        if priority_title in lower:
            return idx
    return 998


def _extract_domain(website: str | None) -> str | None:
    if not website:
        return None

    parsed = urlparse(website if "://" in website else f"https://{website}")
    hostname = parsed.hostname or ""
    hostname = hostname.lower().lstrip("www.")
    return hostname or None


def find_clinic_contacts(name: str, city: str, state: str, website: str | None = None) -> list[ApolloContact]:
    """
    Query Apollo API for contacts at the given clinic.
    Returns contacts sorted by title priority, filtered to verified emails only.
    """
    payload = {
        "q_organization_name": name,
        "q_organization_locations": [f"{city}, {state}"],
        "titles": PRIORITY_TITLES,
        "per_page": 10,
    }

    domain = _extract_domain(website)
    if domain:
        payload["q_organization_domains"] = [domain]

    try:
        response = httpx.post(
            APOLLO_PEOPLE_URL,
            json=payload,
            headers={"X-Api-Key": config.APOLLO_API_KEY, "Content-Type": "application/json"},
            timeout=30,
        )
    except httpx.RequestError:
        return []

    if response.status_code != 200:
        return []

    data = response.json()
    people = data.get("people", [])

    contacts: list[ApolloContact] = []
    seen_emails: set[str] = set()
    for person in people:
        email = person.get("email", "")
        status = person.get("email_status", "")
        if not email or status not in VALID_EMAIL_STATUSES:
            continue
        normalized_email = email.lower().strip()
        if normalized_email in seen_emails:
            continue
        seen_emails.add(normalized_email)

        contacts.append(ApolloContact(
            email=email,
            first_name=person.get("first_name"),
            last_name=person.get("last_name"),
            title=person.get("title"),
            confidence_score=1.0 if status == "verified" else 0.7,
        ))

    contacts.sort(key=lambda c: _title_priority(c.title))
    return contacts
