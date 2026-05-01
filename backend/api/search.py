from fastapi import APIRouter
from services.retriever import RetrieverService

router = APIRouter()
retriever = RetrieverService()

@router.get("/search/{session_id}")
async def search_documents(query: str, top_k: int = 5):
    results = retriever.search(
        query=query,
        top_k=top_k
    )

    return {
        "query": query,
        "results": results
    }