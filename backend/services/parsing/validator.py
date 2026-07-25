import logging

from fastapi import HTTPException, UploadFile

from config.constants import (
    UPLOAD_MAX_SIZE_MB,
    UPLOAD_MAX_PAGES,
    UPLOAD_MAX_TEXT_LENGTH,
    UPLOAD_ALLOWED_EXTENSIONS,
)

logger = logging.getLogger(__name__)

PDF_MAGIC = b"%PDF"
DOCX_MAGIC = b"PK\x03\x04"


def _read_bytes(content: bytes, offset: int, length: int) -> bytes:
    return content[offset : offset + length]


def verify_file_type(content: bytes, filename: str) -> str:
    ext = ""
    idx = filename.rfind(".")
    if idx != -1:
        ext = filename[idx:].lower()

    if ext not in UPLOAD_ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported file type '{ext}'. Accepted: PDF, DOCX.",
        )

    header = _read_bytes(content, 0, 4)

    if ext == ".pdf" and not header.startswith(PDF_MAGIC):
        raise HTTPException(
            status_code=422,
            detail="File has .pdf extension but is not a valid PDF (bad magic bytes).",
        )
    if ext == ".docx" and not header.startswith(DOCX_MAGIC):
        raise HTTPException(
            status_code=422,
            detail="File has .docx extension but is not a valid DOCX (bad magic bytes).",
        )

    return ext


def validate_file_size(content: bytes) -> None:
    size_mb = len(content) / (1024 * 1024)
    if size_mb > UPLOAD_MAX_SIZE_MB:
        raise HTTPException(
            status_code=422,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {UPLOAD_MAX_SIZE_MB} MB.",
        )


def validate_page_count(doc) -> None:
    page_count = len(doc)
    if page_count > UPLOAD_MAX_PAGES:
        raise HTTPException(
            status_code=422,
            detail=f"PDF has {page_count} pages. Maximum is {UPLOAD_MAX_PAGES} pages.",
        )


def validate_text_length(text: str) -> str:
    if len(text) > UPLOAD_MAX_TEXT_LENGTH:
        raise HTTPException(
            status_code=422,
            detail=f"Extracted text too long ({len(text)} chars). Maximum is {UPLOAD_MAX_TEXT_LENGTH} characters.",
        )
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="No readable text found in the document.",
        )
    return text
