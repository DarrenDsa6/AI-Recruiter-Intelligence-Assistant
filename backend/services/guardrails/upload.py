import logging

from config.constants import UPLOAD_MAX_SIZE_MB, UPLOAD_MAX_TEXT_LENGTH

logger = logging.getLogger(__name__)


def validate_upload(text: str, filename: str, user_id=None) -> str | None:
    from services.guardrails.injection import check_document_injection_regex
    from services.guardrails.moderation import check_content_moderation

    injection_findings = check_document_injection_regex(text)
    if injection_findings:
        logger.warning(
            f"Prompt injection detected in upload: user={user_id}, file={filename}, "
            f"findings={injection_findings}"
        )
        return "Document contains suspicious content and was rejected."

    mod_result = check_content_moderation(text)
    if mod_result:
        logger.warning(f"Content moderation flag: user={user_id}, file={filename}, reason={mod_result}")
        return "Document was rejected by content moderation."

    return None


def validate_jd_text(jd_text: str, user_id=None) -> str | None:
    from services.guardrails.injection import check_document_injection_regex
    from services.guardrails.moderation import check_content_moderation

    if not jd_text or not jd_text.strip():
        return "Job description text is required."

    if len(jd_text) > UPLOAD_MAX_TEXT_LENGTH:
        return f"Job description too long ({len(jd_text)} chars). Maximum is {UPLOAD_MAX_TEXT_LENGTH}."

    injection_findings = check_document_injection_regex(jd_text)
    if injection_findings:
        logger.warning(f"Prompt injection in JD: user={user_id}, findings={injection_findings}")
        return "Job description contains suspicious content."

    mod_result = check_content_moderation(jd_text)
    if mod_result:
        logger.warning(f"Content moderation flag in JD: user={user_id}, reason={mod_result}")
        return "Job description was rejected by content moderation."

    return None
