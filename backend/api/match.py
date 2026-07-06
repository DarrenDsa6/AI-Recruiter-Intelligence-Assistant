from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import time
import logging

from services.matcher import MatcherService
from services.vector_store import vector_store
from services.github_service import GitHubService
from services.llm_service import llm_service
from services.provider_config import PROVIDER_CONFIGS

logger = logging.getLogger(__name__)
router = APIRouter()

matcher = MatcherService(llm_service)
github_service = GitHubService()


class MatchRequest(BaseModel):
    session_id: str
    job_description: str
    github_username: str | None = None
    github_token: str | None = None
    provider: str = "openai"
    model: str = "gpt-4o-mini"
    api_key: str = ""
    base_url: str = ""


def _llm_config(provider, model, api_key, base_url=""):
    if base_url:
        return api_key, base_url, model
    provider_cfg = PROVIDER_CONFIGS.get(provider)
    resolved = provider_cfg["base_url"] if provider_cfg else PROVIDER_CONFIGS["openai"]["base_url"]
    return api_key, resolved, model


@router.post("/match")
async def match_job_description(request: MatchRequest):
    start_time = time.time()

    if not request.api_key:
        return {"error": "API key is required"}

    stored_data = vector_store.get_by_session(request.session_id)

    if not stored_data or not stored_data.get("documents"):
        return {"error": "Session not found"}

    resume_text = " ".join(stored_data["documents"])
    logger.info(f"Match: resume length {len(resume_text)} chars")

    github_data = []

    if request.github_username:
        try:
            gh_service = GitHubService(token=request.github_token) if request.github_token else github_service
            github_data = gh_service.get_repositories(request.github_username)
            logger.info(f"GitHub: {len(github_data)} repos for {request.github_username}")
        except Exception as e:
            logger.error(f"GitHub error: {e}")

    api_key, base_url, model = _llm_config(request.provider, request.model, request.api_key, request.base_url)

    result = await matcher.full_analysis(
        resume={"text": resume_text},
        jd={"text": request.job_description},
        github_data=github_data,
        session_id=request.session_id,
        api_key=api_key,
        base_url=base_url,
        model=model,
    )

    total_time = round(time.time() - start_time, 2)
    logger.info(f"Match completed in {total_time}s")

    return result


@router.post("/match/stream")
async def stream_match(request: MatchRequest):
    stored_data = vector_store.get_by_session(request.session_id)

    if not stored_data or not stored_data.get("documents"):
        return {"error": "Session not found"}

    resume_text = " ".join(stored_data["documents"])
    api_key, base_url, model = _llm_config(request.provider, request.model, request.api_key, request.base_url)

    async def generator():
        prompt = f"""
You are a strict recruiter AI.

Analyze this candidate:

Resume:
{resume_text}

Job Description:
{request.job_description}

Give detailed reasoning, strengths, weaknesses, and final verdict.
"""

        try:
            async for token in llm_service._stream(prompt, api_key, base_url, model):
                yield token
        except Exception as e:
            yield f"\n[ERROR]: {str(e)}"

    return StreamingResponse(generator(), media_type="text/plain")
