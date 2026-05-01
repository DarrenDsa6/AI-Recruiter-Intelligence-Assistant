from fastapi import APIRouter
from pydantic import BaseModel

from services.matcher import MatcherService
from services.vector_store import VectorStoreService
from services.github_service import GitHubService
from services.llm_service import LLMRecruiterService

router = APIRouter()

llm = LLMRecruiterService(api_key="YOUR_API_KEY")
matcher = MatcherService(llm)
vector_store = VectorStoreService()
github_service = GitHubService()


class MatchRequest(BaseModel):
    session_id: str
    job_description: str
    github_username: str | None = None


@router.post("/match")
async def match_job_description(request: MatchRequest):

    # Get FULL session data
    session_text = vector_store.get_session_text(
        request.session_id
    )

    if not session_text:
        return {"error": "Session not found"}

    github_data = []

    if request.github_username:
        github_data = github_service.get_repositories(
            request.github_username
        )

    result = matcher.full_analysis(
        resume={"text": session_text},
        jd={"text": request.job_description},
        github_data=github_data,
        session_id=request.session_id
    )

    return result