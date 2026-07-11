from pydantic import BaseModel
from uuid import UUID


class MatchRequest(BaseModel):
    resume_id: UUID
    jd_text: str


class MatchAccepted(BaseModel):
    report_id: UUID
    status: str = "pending"
    message: str = "Analysis queued. Check your email in ~2 minutes."
