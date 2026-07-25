import re
import logging

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

DOCUMENT_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions",
    r"you\s+are\s+now\s+(a|an|the)",
    r"pretend\s+you\s+(are|were|have)",
    r"act\s+as\s+if\s+you",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|instructions)",
    r"new\s+instructions?\s*:",
    r"system\s*prompt\s*:",
    r"override\s+(your\s+)?instructions?",
    r"reveal\s+(your\s+)?(system\s+prompt|instructions?|rules?)",
    r"<\|im_start\|>",
    r"<\|im_end\|>",
    r"\[INST\]|\[/INST\]",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
]


def check_injection_regex(message: str) -> bool:
    lower = message.lower()
    return any(re.search(p, lower) for p in INJECTION_PATTERNS)


def check_document_injection_regex(text: str) -> list[str]:
    lower = text.lower()
    findings = []
    for p in DOCUMENT_INJECTION_PATTERNS:
        match = re.search(p, lower)
        if match:
            findings.append(match.group())
    return findings


async def check_injection_llm(text: str) -> dict:
    try:
        from services.llm import llm_client
        truncated = text[:2000]
        result = await llm_client.detect_injection(truncated)
        return result
    except Exception as e:
        logger.error(f"LLM injection check failed: {e}")
        return {"is_injection": False, "confidence": 0.0, "error": str(e)}


async def check_injection(message: str) -> dict:
    regex_hit = check_injection_regex(message)
    if regex_hit:
        return {"is_injection": True, "confidence": 1.0, "method": "regex"}

    llm_result = await check_injection_llm(message)
    if llm_result.get("is_injection") and llm_result.get("confidence", 0) >= 0.7:
        return {"is_injection": True, "confidence": llm_result["confidence"], "method": "llm"}

    return {"is_injection": False, "confidence": 0.0, "method": "none"}


async def check_document_injection(text: str) -> list[str]:
    findings = check_document_injection_regex(text)
    if findings:
        return findings

    llm_result = await check_injection_llm(text)
    if llm_result.get("is_injection") and llm_result.get("confidence", 0) >= 0.7:
        return [f"LLM detected injection (confidence: {llm_result['confidence']:.2f})"]

    return []
