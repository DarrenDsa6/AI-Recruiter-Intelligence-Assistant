from fastapi import APIRouter

from services.github_service import GitHubService
from services.chunker import ChunkerService
from services.embedding_service import EmbedderService
from services.vector_store import VectorStoreService

router = APIRouter()

github_service = GitHubService()
chunker = ChunkerService()
embedder = EmbedderService()
vector_store = VectorStoreService()

@router.post("/github/{session_id}/{username}")
async def ingest_github(session_id: str, username: str):
    repos = github_service.get_repositories(username)
    chunks = []
    metadatas = []

    for repo in repos:
        readme = github_service.get_readme(username, repo["name"])

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

    return {
        "repos": len(repos),
        "chunks": len(chunks)
    }