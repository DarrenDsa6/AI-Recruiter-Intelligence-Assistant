from pydantic import BaseModel, Field
from uuid import UUID


class MatchRequest(BaseModel):
    resume_id: UUID
    jd_text: str = Field(..., max_length=50000)
    send_email: bool = False


class MatchAccepted(BaseModel):
    report_id: UUID
    status: str = "pending"
    message: str = "Analysis queued. Check the dashboard for results."
