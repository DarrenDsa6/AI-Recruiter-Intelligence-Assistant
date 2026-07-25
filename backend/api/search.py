import asyncio
import logging
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.embedding import embedder
from services.storage import vector_store
from models.resume import MasterResume

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/search/{resume_id}")
async def search_documents(
    resume_id: str,
    query: str,
    top_k: int = 5,
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
        stored_data = await vector_store.get_by_resume(db, resume_id)
        if not stored_data or not stored_data.get("documents"):
            raise HTTPException(status_code=404, detail="No documents found for this resume")

        query_emb = (await asyncio.to_thread(embedder.get_embeddings, [query]))[0]
        doc_embeddings = stored_data.get("embeddings", [])
        docs = stored_data.get("documents", [])

        if not doc_embeddings:
            return {"results": []}

        scores = cosine_similarity([query_emb], doc_embeddings)[0]
        top_indices = np.argsort(scores)[-top_k:][::-1]

        results = [{"text": docs[idx], "score": round(float(scores[idx]), 4)} for idx in top_indices]
        return {"query": query, "results": results}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed. Please try again.")
