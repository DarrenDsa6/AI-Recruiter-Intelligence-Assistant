from fastapi import APIRouter
import logging

from services.vector_store import vector_store
from services.embedding_service import embedder

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search/{session_id}")
async def search_documents(session_id: str, query: str, top_k: int = 5):
    try:
        stored_data = vector_store.get_by_session(session_id)
        if not stored_data or not stored_data.get("documents"):
            return {"error": "Session not found"}

        query_emb = embedder.get_embeddings([query])[0]
        doc_embeddings = stored_data.get("embeddings", [])
        docs = stored_data.get("documents", [])

        if not doc_embeddings:
            return {"results": []}

        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity

        scores = cosine_similarity([query_emb], doc_embeddings)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = []
        for idx in top_indices:
            results.append({
                "text": docs[idx],
                "score": round(float(scores[idx]), 4)
            })

        return {"query": query, "results": results}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"error": str(e)}
