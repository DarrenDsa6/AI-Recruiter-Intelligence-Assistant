import re
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RESUME_SIGNALS = [
    r"\b(resume|curriculum\s+vitae|cv)\b",
    r"\b(work\s+history)\b",
    r"\b(gpa)\b",
    r"\b(summary|objective|profile)\s*:?\s*\n",
    r"\b(certifications?|licenses?|awards?)\s*:?\s*\n",
    r"\b(references?|portfolio)\s*:?\s*\n",
    r"\b(contact|email|phone|linkedin)\s*:?\s*\S+",
    r"\b(full\s+stack|backend|frontend|devops)\s+(engineer|developer)\b",
    r"\b(bachelor|master|phd|b\.?s\.?|m\.?s\.?)\s+(of|in)\b",
    r"\b(\d{4}\s*[-–]\s*(?:present|current|\d{4}))\b",
    r"\b(led|managed|developed|designed|implemented|built|launched)\b.*\b(team|project|system|application)\b",
]

JD_SIGNALS = [
    r"\b(job\s+description|position\s+description|role\s+description)\b",
    r"\b(responsibilities|duties)\b",
    r"\b(requirements|minimum\s+requirements|basic\s+requirements)\b",
    r"\b(qualifications|desired\s+qualifications|preferred\s+qualifications)\b",
    r"\b(we\s+are\s+looking|we\s+are\s+seeking|looking\s+for\s+a)\b",
    r"\b(the\s+ideal\s+candidate|the\s+successful\s+candidate)\b",
    r"\b(what\s+you.ll\s+do|what\s+you.ll\s+be\s+doing)\b",
    r"\b(about\s+the\s+role|about\s+us|about\s+the\s+company)\b",
    r"\b(apply\s+now|submit\s+your|join\s+our\s+team)\b",
    r"\b(offer|compensation|benefits|perks)\b",
    r"\b(reporting\s+to|reports\s+to|manages?)\b",
]

HIGH_CONFIDENCE_THRESHOLD = 0.80
MIN_SIGNALS_FOR_FAST_PATH = 3
MIN_SCORE_GAP = 2


@dataclass
class ClassificationResult:
    doc_type: str
    confidence: float
    tier: str


def _score_signals(text: str, patterns: list[str]) -> int:
    lower = text.lower()
    return sum(1 for p in patterns if re.search(p, lower))


def _heuristic_classify(text: str) -> ClassificationResult:
    if not text or not text.strip():
        return ClassificationResult(doc_type="other", confidence=1.0, tier="heuristic")

    truncated = text[:10000]
    resume_score = _score_signals(truncated, RESUME_SIGNALS)
    jd_score = _score_signals(truncated, JD_SIGNALS)

    logger.debug(f"Heuristic scores: resume={resume_score}, jd={jd_score}")

    max_possible = max(len(RESUME_SIGNALS), len(JD_SIGNALS))
    total_hits = resume_score + jd_score

    if resume_score >= MIN_SIGNALS_FOR_FAST_PATH and resume_score - jd_score >= MIN_SCORE_GAP:
        confidence = min(1.0, 0.5 + (resume_score / max_possible) * 0.5)
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return ClassificationResult(doc_type="resume", confidence=confidence, tier="heuristic")

    if jd_score >= MIN_SIGNALS_FOR_FAST_PATH and jd_score - resume_score >= MIN_SCORE_GAP:
        confidence = min(1.0, 0.5 + (jd_score / max_possible) * 0.5)
        if confidence >= HIGH_CONFIDENCE_THRESHOLD:
            return ClassificationResult(doc_type="jd", confidence=confidence, tier="heuristic")

    if resume_score >= 2 and resume_score > jd_score:
        confidence = min(0.79, 0.4 + (resume_score / max_possible) * 0.4)
        return ClassificationResult(doc_type="resume", confidence=confidence, tier="heuristic")

    if jd_score >= 2 and jd_score > resume_score:
        confidence = min(0.79, 0.4 + (jd_score / max_possible) * 0.4)
        return ClassificationResult(doc_type="jd", confidence=confidence, tier="heuristic")

    if total_hits == 0:
        return ClassificationResult(doc_type="other", confidence=0.9, tier="heuristic")

    return ClassificationResult(doc_type="other", confidence=0.3, tier="heuristic")


async def classify_document(text: str) -> ClassificationResult:
    """Classify document as resume, jd, or other.

    Tier 1: Fast keyword heuristics.
    Tier 2: LLM fallback when heuristic confidence is low.

    Returns ClassificationResult with doc_type, confidence, and tier.
    """
    if not text or not text.strip():
        return ClassificationResult(doc_type="other", confidence=1.0, tier="heuristic")

    heuristic = _heuristic_classify(text)
    logger.info(
        f"Heuristic classification: type={heuristic.doc_type}, "
        f"confidence={heuristic.confidence:.2f}"
    )

    if heuristic.confidence >= HIGH_CONFIDENCE_THRESHOLD:
        return heuristic

    logger.info(
        f"Low confidence ({heuristic.confidence:.2f}), falling back to LLM classifier"
    )

    try:
        from services.llm import llm_client
        llm_result = await llm_client.classify_document(text)
        llm_type = llm_result.get("type", "other")
        llm_confidence = float(llm_result.get("confidence", 0.0))

        logger.info(f"LLM classification: type={llm_type}, confidence={llm_confidence:.2f}")

        if llm_confidence >= 0.7:
            return ClassificationResult(
                doc_type=llm_type,
                confidence=llm_confidence,
                tier="llm",
            )

        if llm_type == heuristic.doc_type:
            merged_confidence = max(heuristic.confidence, llm_confidence)
            return ClassificationResult(
                doc_type=llm_type,
                confidence=merged_confidence,
                tier="consensus",
            )

        logger.warning(
            f"Classification mismatch: heuristic={heuristic.doc_type} ({heuristic.confidence:.2f}), "
            f"llm={llm_type} ({llm_confidence:.2f}). Using heuristic."
        )
        return heuristic

    except Exception as e:
        logger.error(f"LLM classifier failed: {e}, falling back to heuristic")
        return heuristic
