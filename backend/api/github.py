import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
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


@router.post("/github/{resume_id}/{username}")
async def ingest_github(
    resume_id: str,
    username: str,
    token: str | None = None,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MasterResume.id).where(
            MasterResume.id == resume_id,
            MasterResume.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Resume not found")

    try:
        gh_service = GitHubService(token=token) if token else GitHubService()
        repos = await gh_service.get_repositories(username)
        chunks = []
        metadatas = []

        for repo in repos:
            combined = f"Repo: {repo['name']}\nDesc: {repo['description']}\nURL: {repo['url']}\nREADME:\n{repo['readme']}"

            for chunk in chunker.chunk_text(combined):
                chunks.append(chunk)
                metadatas.append({"source": "github", "repo_name": repo["name"], "repo_url": repo["url"]})

        if not chunks:
            return {"message": "No data"}

        embeddings = embedder.embed_documents(chunks)
        await vector_store.add_documents(db=db, documents=chunks, embeddings=embeddings, metadatas=metadatas, resume_id=resume_id)
        await db.commit()

        logger.info(f"GitHub ingest: {len(repos)} repos, {len(chunks)} chunks for {username}")
        return {"repos": len(repos), "chunks": len(chunks)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"GitHub ingest failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
