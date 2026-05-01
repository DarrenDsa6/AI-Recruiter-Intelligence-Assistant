from fastapi import APIRouter, UploadFile, File

from services.parser import ParserService
from services.chunker import ChunkerService
from services.embedding_service import EmbedderService
from services.vector_store import VectorStoreService
from services.skills import SkillExtractionService
from services.session_store import SessionStore

router = APIRouter()

parser = ParserService()
chunker = ChunkerService()
embedder = EmbedderService()
vector_store = VectorStoreService()
skill_extractor = SkillExtractionService()
session_store = SessionStore()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
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

    # CREATE SESSION FIRST
    session_id = session_store.create_session()

    # STORE WITH SESSION
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

    return {
        "session_id": session_id,
        "filename": file.filename,
        "skills": resume_skills
    }