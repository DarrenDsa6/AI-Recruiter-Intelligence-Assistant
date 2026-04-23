from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.matcher import MatcherService

router = APIRouter()
matcher = MatcherService()

class JDRequest(BaseModel):
    job_description: str = Field(
        ...,
        title="Job Description",
        description="Paste full multi-line job description here",
        example="""
            Looking for a Python developer with:

            - FastAPI
            - Machine Learning
            - RAG pipelines
            - React frontend
            - Docker
            """
    )

@router.post("/match")
async def match_job_description(request: JDRequest):
    result = matcher.compute_similarity(
        jd_text=request.job_description
    )

    return result