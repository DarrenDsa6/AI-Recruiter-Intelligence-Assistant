from pydantic import BaseModel
from uuid import UUID


class ChatRequest(BaseModel):
    resume_id: UUID
    report_id: UUID
    message: str
