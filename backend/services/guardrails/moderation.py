import re
import logging

logger = logging.getLogger(__name__)

CONTENT_MODERATION_PATTERNS = [
    r"\b(kill\s+yourself|kys)\b",
    r"\b(hate\s+speech|racial\s+slur)\b",
    r"\b(suicide|self[- ]harm)\b",
    r"\b(gore|graphic\s+violence)\b",
    r"\b(sexual\s+content|nsfw|porn)\b",
    r"\b(drug\s+(use|manufacture|sale)|illicit\s+substances)\b",
]


def check_content_moderation(text: str) -> str | None:
    lower = text.lower()
    for p in CONTENT_MODERATION_PATTERNS:
        match = re.search(p, lower)
        if match:
            return f"Document contains potentially unsafe content: '{match.group()}'"
    return None
