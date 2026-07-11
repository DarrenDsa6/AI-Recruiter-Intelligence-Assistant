from pydantic import BaseModel
from uuid import UUID


class UploadResponse(BaseModel):
    resume_id: UUID
    filename: str
    skills: list[str]


class UploadDuplicateResponse(BaseModel):
    resume_id: UUID
    filename: str
    message: str
