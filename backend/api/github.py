import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.integrations import GitHubService
from services.parsing import ChunkerService
from services.embedding import embedder
from services.storage import vector_store

logger = logging.getLogger(__name__)
router = APIRouter()

chunker = ChunkerService()


@router.post("/github/{session_id}/{username}")
async def ingest_github(
    session_id: str,
    username: str,
    token: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    try:
        gh_service = GitHubService(token=token) if token else GitHubService()
        repos = gh_service.get_repositories(username)
        chunks = []
        metadatas = []

        for repo in repos:
            readme = gh_service.get_readme(username, repo["name"])
            combined = f"Repo: {repo['name']}\nDesc: {repo['description']}\nURL: {repo['url']}\nREADME:\n{readme}"

            for chunk in chunker.chunk_text(combined):
                chunks.append(chunk)
                metadatas.append({"source": "github", "repo_name": repo["name"], "repo_url": repo["url"]})

        if not chunks:
            return {"message": "No data"}

        embeddings = embedder.embed_documents(chunks)
        await vector_store.add_documents(db=db, documents=chunks, embeddings=embeddings, metadatas=metadatas, resume_id=session_id)
        await db.commit()

        logger.info(f"GitHub ingest: {len(repos)} repos, {len(chunks)} chunks for {username}")
        return {"repos": len(repos), "chunks": len(chunks)}
    except Exception as e:
        logger.error(f"GitHub ingest failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))
