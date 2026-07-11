import hashlib
import logging
from uuid import UUID

from fastapi import APIRouter, UploadFile, File, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.parser import ParserService
from services.chunker import ChunkerService
from services.embedding_service import embedder
from services.vector_store import vector_store
from services.skills import SkillExtractionService
from services.db import get_db
from models.resume import MasterResume
from schemas.upload import UploadResponse, UploadDuplicateResponse
from schemas.common import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()

parser = ParserService()
chunker = ChunkerService()
skill_extractor = SkillExtractionService()


def _hash_file(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


async def _get_user_id(authorization: str = Header(...)) -> UUID:
    import jwt
    import os
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, os.environ.get("JWT_SECRET", ""), algorithms=["HS256"])
    return UUID(payload["sub"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        content = await file.read()
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

        text = parser.parse_file(file_bytes=content, filename=file.filename)
        resume_skills = skill_extractor.extract_skills(text)
        chunks = chunker.chunk_text(text)

        if not chunks:
            return ErrorResponse(error="Chunking failed")

        embeddings = embedder.embed_documents(chunks)
        if not embeddings:
            return ErrorResponse(error="Embedding failed")

        resume = MasterResume(
            user_id=user_id,
            file_hash=file_hash,
            raw_text=text,
            chroma_resume_id="",
            filename=file.filename,
        )
        db.add(resume)
        await db.commit()
        await db.refresh(resume)

        await vector_store.add_documents(
            db=db,
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {"source": "resume", "skills": ", ".join(resume_skills)}
                for _ in chunks
            ],
            resume_id=str(resume.id),
        )
        await db.commit()

        resume.chroma_resume_id = str(resume.id)
        await db.commit()

        logger.info(f"Resume {resume.id}: {len(chunks)} chunks stored for {file.filename}")
        return UploadResponse(resume_id=resume.id, filename=file.filename, skills=resume_skills)

    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return ErrorResponse(error=str(e))
