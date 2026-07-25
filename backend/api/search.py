import logging

import numpy as np
from fastapi import APIRouter, Depends
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from services.embedding import embedder
from services.storage import vector_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search/{session_id}")
async def search_documents(session_id: str, query: str, top_k: int = 5, db: AsyncSession = Depends(get_db)):
    try:
        stored_data = await vector_store.get_by_resume(db, session_id)
        if not stored_data or not stored_data.get("documents"):
            return {"error": "Session not found"}

        query_emb = embedder.get_embeddings([query])[0]
        doc_embeddings = stored_data.get("embeddings", [])
        docs = stored_data.get("documents", [])

        if not doc_embeddings:
            return {"results": []}

        scores = cosine_similarity([query_emb], doc_embeddings)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = [{"text": docs[idx], "score": round(float(scores[idx]), 4)} for idx in top_indices]
        return {"query": query, "results": results}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"error": str(e)}
