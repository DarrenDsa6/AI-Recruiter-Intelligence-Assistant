import re
import logging

from config.constants import MAX_MESSAGE_LENGTH, RATE_LIMIT_MAX_MESSAGES, RATE_LIMIT_WINDOW_SECONDS

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions",
    r"you\s+are\s+now\s+(a|an|the)",
    r"pretend\s+you\s+(are|were|have)",
    r"act\s+as\s+if\s+you",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|instructions)",
    r"new\s+instructions?\s*:",
    r"system\s*prompt\s*:",
    r"override\s+(your\s+)?instructions?",
    r"jailbreak",
    r"DAN\s+mode",
    r"developer\s+mode",
    r"you\s+are\s+now\s+unrestricted",
    r"bypass\s+(all\s+)?(filters|restrictions|rules|guidelines)",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions?|rules?)",
    r"what\s+(are|is)\s+your\s+(system\s+prompt|instructions?)",
]

OFF_TOPIC_KEYWORDS = [
    r"\b(weather|forecast|temperature)\b",
    r"\b(stock|crypto|bitcoin|ethereum|trading)\b",
    r"\b(recipe|cook|bake|ingredient)\b",
    r"\b(movie|tv\s+show|netflix|spotify|music)\b",
    r"\b(sports?|nba|nfl|fifa|world\s+cup)\b",
    r"\b(politics|election|vote|democrat|republican)\b",
    r"\b(religion|god|bible|quran|prayer)\b",
    r"\b(dating|relationship|girlfriend|boyfriend)\b",
    r"\b(write\s+a\s+(story|poem|novel|essay))\b",
    r"\b(translate\s+(to|into)\s+(spanish|french|chinese|german))\b",
    r"\b(play\s+a\s+game|riddle|trivia|puzzle)\b",
    r"\b(how\s+do\s+i\s+(hack|crack|exploit))\b",
    r"\b(illegal|unlawful|fraud|scam)\b",
]

CODE_BLOCK_PATTERN = re.compile(r"```[\s\S]*?```", re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r"`[^`]+`")
URL_PATTERN = re.compile(r"https?://[^\s\)>\]\"]+", re.IGNORECASE)
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\([^\)]+\)")


def check_injection(message: str) -> bool:
    lower = message.lower()
    return any(re.search(p, lower) for p in INJECTION_PATTERNS)


def check_off_topic(message: str) -> bool:
    lower = message.lower()
    return sum(1 for p in OFF_TOPIC_KEYWORDS if re.search(p, lower)) >= 2


def validate_message(message: str) -> str | None:
    if not message or not message.strip():
        return "Message cannot be empty."
    if len(message) > MAX_MESSAGE_LENGTH:
        return f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters."
    if check_injection(message):
        return "Your message was blocked. Please ask about your resume, skills, or the target role."
    if check_off_topic(message):
        return "I can only help with resume and job application questions. Please ask about your resume, skills, or the target role."
    return None


def sanitize_output(text: str) -> str:
    text = CODE_BLOCK_PATTERN.sub("", text)
    text = INLINE_CODE_PATTERN.sub("", text)
    text = MARKDOWN_LINK_PATTERN.sub(r"\1", text)
    text = URL_PATTERN.sub("[link removed]", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


async def check_rate_limit(redis, session_key: str) -> str | None:
    rate_key = f"chat_rate:{session_key}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, RATE_LIMIT_WINDOW_SECONDS)
    if count > RATE_LIMIT_MAX_MESSAGES:
        return f"Rate limit exceeded. Max {RATE_LIMIT_MAX_MESSAGES} messages per hour."
    return None
