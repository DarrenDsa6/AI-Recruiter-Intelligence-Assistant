import hashlib
import logging
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.parsing import ParserService, ChunkerService, SkillExtractionService
from services.parsing.validator import (
    verify_file_type,
    validate_file_size,
    validate_text_length,
)
from services.parsing.classifier import classify_document
from services.guardrails import validate_upload
from services.embedding import embedder
from services.storage import vector_store
from models.resume import MasterResume
from schemas.upload import UploadResponse, UploadDuplicateResponse, UploadRejectResponse

logger = logging.getLogger(__name__)
router = APIRouter()

parser = ParserService()
chunker = ChunkerService()
skill_extractor = SkillExtractionService()


def _hash_file(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        content = await file.read()

        validate_file_size(content)
        file_ext = verify_file_type(content, file.filename or "")

        file_hash = _hash_file(content)

        result = await db.execute(
            select(MasterResume).where(
                MasterResume.user_id == user_id,
                MasterResume.file_hash == file_hash,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            logger.info(f"Duplicate resume detected: {existing.id}")
            return UploadDuplicateResponse(
                resume_id=existing.id,
                filename=existing.filename or file.filename,
                message="Resume already uploaded.",
            )

        text = parser.parse_file(file_bytes=content, filename=file.filename or "")
        text = validate_text_length(text)

        classification = await classify_document(text)
        logger.info(
            f"Document classified as {classification.doc_type} "
            f"(confidence={classification.confidence:.2f}, tier={classification.tier}): "
            f"{file.filename}"
        )
        if classification.doc_type == "other":
            logger.warning(f"Rejected document (not resume or JD): user={user_id}, file={file.filename}")
            return UploadRejectResponse(
                reason="Document could not be classified as a resume or job description. Please upload a valid resume.",
                filename=file.filename,
            )

        guardrail_error = validate_upload(text, file.filename, user_id)
        if guardrail_error:
            return UploadRejectResponse(reason=guardrail_error, filename=file.filename)

        resume_skills = skill_extractor.extract_skills(text)
        chunk_dicts = chunker.chunk_text(text)

        if not chunk_dicts:
            return UploadRejectResponse(
                reason="Could not extract meaningful content from the document.",
                filename=file.filename,
            )

        chunk_texts = [c["text"] for c in chunk_dicts]
        embeddings = embedder.embed_documents(chunk_texts)
        if not embeddings:
            return UploadRejectResponse(
                reason="Failed to generate embeddings for the document.",
                filename=file.filename,
            )

        resume = MasterResume(
            user_id=user_id,
            file_hash=file_hash,
            raw_text=text,
            filename=file.filename,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        metadatas = [
            {"source": "resume", "skills": ", ".join(resume_skills), "chunk_start": c["start"], "chunk_end": c["end"]}
            for c in chunk_dicts
        ]
        await vector_store.add_documents(
            db=db,
            documents=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas,
            resume_id=str(resume.id),
        )
        await db.commit()

        logger.info(f"Resume {resume.id}: {len(chunks)} chunks stored for {file.filename}")
        return UploadResponse(resume_id=resume.id, filename=file.filename, skills=resume_skills)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise
