from fastapi import APIRouter, UploadFile, File
import logging

from services.parser import ParserService
from services.chunker import ChunkerService
from services.embedding_service import embedder
from services.vector_store import vector_store
from services.skills import SkillExtractionService
from services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter()

parser = ParserService()
chunker = ChunkerService()
skill_extractor = SkillExtractionService()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        content = await file.read()
        text = parser.parse_file(
            file_bytes=content,
            filename=file.filename
        )

        resume_skills = skill_extractor.extract_skills(text)
        chunks = chunker.chunk_text(text)

        if not chunks:
            return {"error": "Chunking failed"}

        embeddings = embedder.embed_documents(chunks)

        if not embeddings:
            return {"error": "Embedding failed"}

        session_id = session_store.create_session()

        vector_store.add_documents(
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {
                    "source": "resume",
                    "skills": resume_skills
                }
                for _ in chunks
            ],
            session_id=session_id
        )

        logger.info(f"Session {session_id}: {len(chunks)} chunks stored for {file.filename}")

        return {
            "session_id": session_id,
            "filename": file.filename,
            "skills": resume_skills
        }
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return {"error": str(e)}
