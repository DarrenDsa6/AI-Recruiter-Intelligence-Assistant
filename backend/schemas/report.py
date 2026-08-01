from pydantic import BaseModel
from datetime import datetime
from uuid import UUID


class ReportListItem(BaseModel):
    id: UUID
    status: str
    jd_text: str
    filename: str | None
    created_at: datetime
    completed_at: datetime | None


class ReportDetail(BaseModel):
    id: UUID
    status: str
    jd_text: str
    match_result: dict | None
    github_analysis: dict | None
    report: dict | None
    questions: dict | None
    rewrites: dict | None
    agent_analysis: dict | None
    interview_prep: dict | None
    outreach_email: dict | None
    error_message: str | None
    created_at: datetime
    completed_at: datetime | None


class ReportStatus(BaseModel):
    id: UUID
    status: str
