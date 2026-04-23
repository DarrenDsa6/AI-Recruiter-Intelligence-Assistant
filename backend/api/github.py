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

@router.post("/github/{username}")
async def ingest_github(username: str):
    print(f"Fetching repositories for: {username}")

    repos = github_service.get_repositories(username)

    print(f"Repositories found: {len(repos)}")

    chunks = []
    metadatas = []

    # Process each repo
    for repo in repos:

        print(f"Processing repo: {repo['name']}")

        readme_text = github_service.get_readme(
            username,
            repo["name"]
        )

        # Combine repo info + README
        combined_text = f"""
            Repository Name: {repo['name']}
            Description: {repo['description']}
            Repository URL: {repo['url']}

            README:
            {readme_text}
        """
        # Chunk text
        repo_chunks = chunker.chunk_text(
            combined_text
        )
        print(
            f"Chunks created for {repo['name']}: {len(repo_chunks)}"
        )

        # Store metadata per chunk
        for chunk in repo_chunks:
            chunks.append(chunk)
            metadatas.append({
                "source": "github",
                "repo_name": repo["name"],
                "repo_url": repo["url"]
            })

    if not chunks:
        return {
            "username": username,
            "message": "No content found to store",
            "repos_found": len(repos)
        }

    print("Total chunks:", len(chunks))

    # Create embeddings
    embeddings = embedder.embed_documents(
        chunks
    )
    print("Embeddings created:", len(embeddings))

    # Store vectors with metadata
    stored_count = vector_store.add_documents(
        documents=chunks,
        embeddings=embeddings,
        metadatas=metadatas
    )
    print("Stored vectors:", stored_count)

    return {
        "username": username,
        "repos_found": len(repos),
        "chunks_created": len(chunks),
        "stored_vectors": stored_count
    }