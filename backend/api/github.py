from fastapi import APIRouter
import logging

from services.github_service import GitHubService
from services.chunker import ChunkerService
from services.embedding_service import embedder
from services.vector_store import vector_store

logger = logging.getLogger(__name__)
router = APIRouter()

github_service = GitHubService()
chunker = ChunkerService()


@router.post("/github/{session_id}/{username}")
async def ingest_github(session_id: str, username: str, token: str | None = None):
    try:
        gh_service = GitHubService(token=token) if token else github_service
        repos = gh_service.get_repositories(username)
        chunks = []
        metadatas = []

        for repo in repos:
            readme = gh_service.get_readme(username, repo["name"])

            combined = f"""
            Repo: {repo['name']}
            Desc: {repo['description']}
            URL: {repo['url']}
            README:
            {readme}
            """

            repo_chunks = chunker.chunk_text(combined)

            for chunk in repo_chunks:
                chunks.append(chunk)
                metadatas.append({
                    "source": "github",
                    "repo_name": repo["name"],
                    "repo_url": repo["url"]
                })

        if not chunks:
            return {"message": "No data"}

        embeddings = embedder.embed_documents(chunks)

        vector_store.add_documents(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            session_id=session_id
        )

        logger.info(f"GitHub ingest: {len(repos)} repos, {len(chunks)} chunks for {username}")

        return {
            "repos": len(repos),
            "chunks": len(chunks)
        }
    except Exception as e:
        logger.error(f"GitHub ingest failed: {e}")
        return {"error": str(e)}
