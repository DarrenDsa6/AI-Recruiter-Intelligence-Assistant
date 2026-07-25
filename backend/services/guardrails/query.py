import re
import logging

from config.constants import RECRUITMENT_KEYWORDS, MAX_MESSAGE_LENGTH

logger = logging.getLogger(__name__)

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

_recruitment_pattern = re.compile(
    "|".join(RECRUITMENT_KEYWORDS), re.IGNORECASE
)


def is_recruitment_related(message: str) -> bool:
    if _recruitment_pattern.search(message):
        return True
    return False


def check_off_topic(message: str) -> bool:
    lower = message.lower()
    return sum(1 for p in OFF_TOPIC_KEYWORDS if re.search(p, lower)) >= 1


async def validate_message(message: str) -> str | None:
    from services.guardrails.injection import check_injection

    if not message or not message.strip():
        return "Message cannot be empty."
    if len(message) > MAX_MESSAGE_LENGTH:
        return f"Message too long. Maximum {MAX_MESSAGE_LENGTH} characters."

    injection_result = await check_injection(message)
    if injection_result["is_injection"]:
        return "Your message was blocked. Please ask about your resume, skills, or the target role."

    if not is_recruitment_related(message):
        return "I can only help with resume and job application questions. Please ask about your resume, skills, or the target role."

    if check_off_topic(message):
        return "I can only help with resume and job application questions. Please ask about your resume, skills, or the target role."

    return None
