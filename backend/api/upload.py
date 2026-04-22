from fastapi import APIRouter, UploadFile, File
import os

from services.parser import DocumentParser
from services.chunker import TextChunker
from services.embedding_service import EmbeddingService

router = APIRouter()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

chunker = TextChunker()
embedder = EmbeddingService()


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):

    file_path = os.path.join(
        UPLOAD_DIR,
        file.filename
    )

    # Save file
    with open(file_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)

    # Parse document
    extracted_text = DocumentParser.parse(file_path)

    # Chunk text
    chunks = chunker.chunk_text(
        extracted_text
    )

    # Store embeddings
    stored_count = embedder.store_embeddings(
        chunks,
        metadata=[
            {"source": file.filename}
            for _ in chunks
        ]
    )

    return {
        "filename": file.filename,
        "status": "uploaded parsed embedded stored",
        "total_chunks": len(chunks),
        "stored_vectors": stored_count
    }