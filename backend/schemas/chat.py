from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional


class ChatRequest(BaseModel):
    resume_id: Optional[UUID] = None
    report_id: UUID
    message: str = Field(..., max_length=2000)
