from pydantic import BaseModel
from uuid import UUID


class MatchRequest(BaseModel):
    resume_id: UUID
    jd_text: str
    send_email: bool = False


class MatchAccepted(BaseModel):
    report_id: UUID
    status: str = "pending"
    message: str = "Analysis queued. Check the dashboard for results."
