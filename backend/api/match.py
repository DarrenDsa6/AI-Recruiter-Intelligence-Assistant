from fastapi import APIRouter
from pydantic import BaseModel

from services.matcher import MatcherService
from services.vector_store import VectorStoreService

router = APIRouter()

matcher = MatcherService()
vector_store = VectorStoreService()

class MatchRequest(BaseModel):
    job_description: str
    resume_id: str


@router.post("/match")
async def match_job_description(request: MatchRequest):
    # Load Resume Text
    resume_text = (
        vector_store
        .get_resume_text(
            request.resume_id
        )
    )

    if not resume_text:
        return {
            "error":
                "Resume not found"
        }

    print(
        "Loaded resume length:",
        len(resume_text)
    )

    # Run Matching
    result = (
        matcher
        .compute_similarity(
            job_description=
                request.job_description
        )
    )

    return result