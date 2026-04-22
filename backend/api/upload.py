from fastapi import APIRouter, UploadFile, File
import os

from services.parser import DocumentParser
from services.chunker import TextChunker

router = APIRouter()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

chunker = TextChunker()


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

    # Chunk document
    chunks = chunker.chunk_text(extracted_text)

    return {
        "filename": file.filename,
        "status": "uploaded parsed and chunked",
        "total_chunks": len(chunks),
        "preview_chunk": chunks[0] if chunks else ""
    }