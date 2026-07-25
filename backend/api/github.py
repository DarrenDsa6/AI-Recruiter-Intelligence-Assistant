import logging
import re
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.integrations import GitHubService
from services.parsing import ChunkerService
from services.embedding import embedder
from services.storage import vector_store
from models.resume import MasterResume

logger = logging.getLogger(__name__)
router = APIRouter()

chunker = ChunkerService()

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
        select(MasterResume.id).where(
            MasterResume.id == resume_id,
            MasterResume.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        gh_service = GitHubService(token=x_github_token) if x_github_token else GitHubService()
        repos = await gh_service.get_repositories(username)
        chunk_texts = []
        metadatas = []

        for repo in repos:
            combined = f"Repo: {repo['name']}\nDesc: {repo['description']}\nURL: {repo['url']}\nREADME:\n{repo['readme']}"

            for chunk in chunker.chunk_text(combined):
                chunk_texts.append(chunk["text"])
                metadatas.append({
                    "source": "github",
                    "repo_name": repo["name"],
                    "repo_url": repo["url"],
                })

        if not chunk_texts:
            return {"message": "No data"}

        embeddings = embedder.embed_documents(chunk_texts)
        await vector_store.add_documents(db=db, documents=chunk_texts, embeddings=embeddings, metadatas=metadatas, resume_id=resume_id)
        await db.commit()

        logger.info(f"GitHub ingest: {len(repos)} repos, {len(chunk_texts)} chunks for {username}")
        return {"repos": len(repos), "chunks": len(chunk_texts)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub ingest failed: {e}")
        raise HTTPException(status_code=400, detail="GitHub ingestion failed. Please try again.")
