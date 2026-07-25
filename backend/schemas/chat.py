from pydantic import BaseModel
from uuid import UUID
from typing import Optional


class ChatRequest(BaseModel):
    resume_id: Optional[UUID] = None
    report_id: UUID
    message: str
