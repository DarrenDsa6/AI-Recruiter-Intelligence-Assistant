import re
import logging

logger = logging.getLogger(__name__)

PII_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")),
    ("phone", re.compile(r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")),
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")),
    ("ip_address", re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")),
    ("street_address", re.compile(
        r"\b\d{1,5}\s+(?:[A-Z][a-zA-Z]*\s+){1,3}(?:Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Court|Ct|Lane|Ln|Way|Place|Pl)\b",
        re.IGNORECASE,
    )),
    ("zip_code", re.compile(r"\b\d{5}(?:-\d{4})?\b")),
]

BLIND_SCREENING_PATTERNS = [
    ("name_prefix", re.compile(r"\b(Mr\.|Mrs\.|Ms\.|Mx\.|Dr\.|Prof\.)\s+[A-Z][a-z]+(\s+[A-Z][a-z]+)?\b", re.IGNORECASE)),
    ("gender_pronouns", re.compile(r"\b(he/him|she/her|they/them|he|she|him|her|his|hers)\b", re.IGNORECASE)),
    ("university_college", re.compile(
        r"\b(University of [A-Z][a-z]+|[A-Z][a-z]+ University|[A-Z][a-z]+ College|MIT|Stanford|Harvard|Yale|Princeton|Columbia|Cornell|Dartmouth|Brown|Penn|Caltech|UCLA|UC Berkeley|Michigan|NYU|USC|Northwestern|Duke|Johns Hopkins|Georgia Tech|UIUC|UT Austin|UW|UBC|McGill|Oxford|Cambridge|Imperial|LSE|Toronto|Waterloo)\b",
        re.IGNORECASE,
    )),
    ("linkedin_url", re.compile(r"https?://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?")),
    ("github_url", re.compile(r"https?://(www\.)?github\.com/[A-Za-z0-9_-]+/?")),
]

REDACTED = "[REDACTED]"


def scrub_pii(text: str) -> str:
    """Replace PII patterns in text with [REDACTED] before sending to LLM."""
    if not text:
        return text

    scrubbed = text
    for pii_type, pattern in PII_PATTERNS:
        matches = pattern.findall(scrubbed)
        if matches:
            logger.debug(f"PII scrubbed: {pii_type} ({len(matches)} instances)")
        scrubbed = pattern.sub(REDACTED, scrubbed)

    return scrubbed


def blind_screening_scrub(text: str) -> str:
    """Redact PII + name indicators, pronouns, and university names for blind screening."""
    if not text:
        return text

    scrubbed = scrub_pii(text)
    for pii_type, pattern in BLIND_SCREENING_PATTERNS:
        matches = pattern.findall(scrubbed)
        if matches:
            logger.debug(f"Blind screening scrub: {pii_type} ({len(matches)} instances)")
        scrubbed = pattern.sub(REDACTED, scrubbed)

    return scrubbed


def has_pii(text: str) -> bool:
    """Check if text contains any PII patterns (for audit logging)."""
    if not text:
        return False
    for _, pattern in PII_PATTERNS:
        if pattern.search(text):
            return True
    return False
