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
