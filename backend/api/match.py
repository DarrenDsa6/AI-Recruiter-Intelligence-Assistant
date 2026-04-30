from fastapi import APIRouter
from pydantic import BaseModel

from services.matcher import MatcherService
from services.vector_store import VectorStoreService
from services.github_service import GitHubService
from services.llm_service import LLMRecruiterService

router = APIRouter()

# -----------------------------
# Services (initialize once)
# -----------------------------
llm = LLMRecruiterService(api_key="YOUR_API_KEY")
matcher = MatcherService(llm)
vector_store = VectorStoreService()
github_service = GitHubService()


class MatchRequest(BaseModel):
    job_description: str
    resume_id: str
    github_username: str | None = None


@router.post("/match")
async def match_job_description(request: MatchRequest):

    # -----------------------------
    # 1. Load Resume
    # -----------------------------
    resume_text = vector_store.get_resume_text(request.resume_id)

    if not resume_text:
        return {"error": "Resume not found"}

    print("Loaded resume length:", len(resume_text))

    # -----------------------------
    # 2. Load GitHub (optional but powerful)
    # -----------------------------
    github_data = []

    if request.github_username:
        github_data = github_service.get_repositories(
            request.github_username
        )

    # -----------------------------
    # 3. FULL AI PIPELINE CALL
    # -----------------------------
    result = matcher.full_analysis(
        resume={
            "text": resume_text
        },
        jd={
            "text": request.job_description
        },
        github_data=github_data
    )

    return result