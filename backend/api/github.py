import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.integrations import GitHubService
from models.chunk import ResumeChunk
from models.resume import MasterResume

logger = logging.getLogger(__name__)
router = APIRouter()

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$")


@router.post("/github/{resume_id}/{username}")
async def ingest_github(
    resume_id: str,
    username: str,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    x_github_token: str | None = Header(default=None, alias="X-GitHub-Token"),
):
    if not _USERNAME_RE.match(username):
        raise HTTPException(status_code=422, detail="Invalid GitHub username format.")

    result = await db.execute(
        select(MasterResume).where(
            MasterResume.id == resume_id,
            MasterResume.user_id == user_id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        gh_service = GitHubService(token=x_github_token) if x_github_token else GitHubService()
        repos = []

        async for repo in gh_service.iter_repositories(username):
            repos.append({
                "name": repo.get("name", ""),
                "description": repo.get("description") or "",
                "url": repo.get("url", ""),
                "stars": repo.get("stars", 0),
                "forks": repo.get("forks", 0),
                "languages": repo.get("languages") or {},
                "readme": (repo.get("readme") or "")[:1500],
            })

        if not repos:
            return {"message": "No data", "repos": 0, "chunks": 0}

        # Remove any legacy GitHub chunks so repo/README text never leaks
        # into resume matching, rewrites, or RAG retrieval. GitHub data is
        # kept only as resume.github_data for the GitHub Insights section.
        await db.execute(
            delete(ResumeChunk).where(
                ResumeChunk.resume_id == resume.id,
                ResumeChunk.section == "github",
            )
        )
        resume.github_data = repos
        await db.commit()

        logger.info(f"GitHub ingest complete: {len(repos)} repos for {username} (resume={resume.id})")
        return {"repos": len(repos), "chunks": 0}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub ingest failed: {e}")
        raise HTTPException(status_code=400, detail="GitHub ingestion failed. Please try again.")
