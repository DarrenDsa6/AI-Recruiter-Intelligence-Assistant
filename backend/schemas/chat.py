from pydantic import BaseModel
from uuid import UUID


class ChatRequest(BaseModel):
    resume_id: UUID
    message: str
