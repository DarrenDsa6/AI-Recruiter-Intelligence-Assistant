from fastapi import APIRouter, UploadFile, File

from services.parser import ParserService
from services.chunker import ChunkerService
from services.embedding_service import EmbedderService
from services.vector_store import VectorStoreService

router = APIRouter()

parser = ParserService()
chunker = ChunkerService()
embedder = EmbedderService()
vector_store = VectorStoreService()


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    # Read file
    content = await file.read()
    # Parse file
    text = parser.parse_file(
        file_bytes=content,
        filename=file.filename
    )
    print("Parsed text length:", len(text))
    # Chunk text
    chunks = chunker.chunk_text(text)
    print("Chunks created:", len(chunks))
    # Create embeddings
    embeddings = embedder.embed_documents(chunks)
    print("Embeddings created:", len(embeddings))
    # Store vectors
    stored_count = vector_store.add_documents(
        documents=chunks,
        embeddings=embeddings
    )
    print("Stored vectors:", stored_count)
    return {
        "filename": file.filename,
        "total_chunks": len(chunks),
        "stored_vectors": stored_count
    }