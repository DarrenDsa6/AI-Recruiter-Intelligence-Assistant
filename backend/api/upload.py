from fastapi import APIRouter, UploadFile, File

from services.parser import ParserService
from services.chunker import ChunkerService
from services.embedding_service import EmbedderService
from services.vector_store import VectorStoreService
from services.skills import SkillExtractionService

router = APIRouter()

parser = ParserService()
chunker = ChunkerService()
embedder = EmbedderService()
vector_store = VectorStoreService()
skill_extractor = SkillExtractionService()

@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Read File
    content = await file.read()
    
    # Parse Resume
    text = parser.parse_file(
        file_bytes=content,
        filename=file.filename
    )
    print("Parsed text length:",
          len(text))
    
    # Extract Skills
    resume_skills = (
        skill_extractor
        .extract_skills(text)
    )

    print(
        "Resume skills extracted:",
        len(resume_skills)
    )

    # Chunk Resume
    chunks = chunker.chunk_text(text)
    print(
        "Chunks created:",
        len(chunks)
    )

    # Create Embeddings
    embeddings = (
        embedder
        .embed_documents(chunks)
    )
    print(
        "Embeddings created:",
        len(embeddings)
    )

    # Store Resume
    resume_id = (
        vector_store
        .add_documents(
            documents=chunks,
            embeddings=embeddings,
            metadata={
                "skills": resume_skills
            }
        )
    )

    print(
        "Stored Resume ID:",
        resume_id
    )

    # Response
    return {
        "filename":
            file.filename,
        "resume_id":
            resume_id,
        "total_chunks":
            len(chunks),
        "skills_extracted":
            resume_skills
    }