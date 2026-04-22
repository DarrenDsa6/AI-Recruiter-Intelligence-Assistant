from fastapi import APIRouter, UploadFile, File
import os

from services.parser import DocumentParser

router = APIRouter()

UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)


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

    # Parse file
    extracted_text = DocumentParser.parse(file_path)

    return {
        "filename": file.filename,
        "status": "uploaded and parsed",
        "preview": extracted_text[:500]
    }