import logging
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sklearn.metrics.pairwise import cosine_similarity

from models.chunk import ResumeChunk
from services.parsing.chunker import BM25Index

logger = logging.getLogger(__name__)

BM25_WEIGHT = 0.3
VECTOR_WEIGHT = 0.7


class VectorStoreService:
    def __init__(self):
        self._bm25_indices: dict[UUID, BM25Index] = {}

    async def add_documents(self, db: AsyncSession, documents, embeddings, metadatas=None, resume_id=None):
        if not documents:
            raise ValueError("No documents provided")
        if not embeddings:
            raise ValueError("Embeddings are empty")
        if len(documents) != len(embeddings):
            raise ValueError("Mismatch: documents vs embeddings")

        chunks = []
        for i in range(len(documents)):
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            chunk = ResumeChunk(
                resume_id=UUID(resume_id) if isinstance(resume_id, str) else resume_id,
                chunk_index=i,
                text=documents[i],
                embedding=embeddings[i],
                skills=meta.get("skills"),
                section=meta.get("section"),
            )
            chunks.append(chunk)

        db.add_all(chunks)
        await db.flush()

        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        self._build_bm25(rid, documents)
        return resume_id

    def _build_bm25(self, resume_id: UUID, documents: list[str]):
        bm25 = BM25Index()
        bm25.build(documents)
        self._bm25_indices[resume_id] = bm25

    async def get_by_resume(self, db: AsyncSession, resume_id, exclude_section: str | None = "github"):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        query = select(ResumeChunk).where(ResumeChunk.resume_id == rid)
        if exclude_section:
            query = query.where(ResumeChunk.section != exclude_section)
        query = query.order_by(ResumeChunk.chunk_index)
        result = await db.execute(query)
        chunks = result.scalars().all()
        if not chunks:
            return {"documents": [], "embeddings": [], "metadatas": []}

        docs = [c.text for c in chunks]
        bm25 = self._bm25_indices.get(rid)
        if bm25 is None or len(bm25.documents) != len(docs):
            self._build_bm25(rid, docs)

        return {
            "documents": docs,
            "embeddings": [list(c.embedding) for c in chunks],
            "metadatas": [{"skills": c.skills or "", "chunk_index": c.chunk_index, "section": c.section or ""} for c in chunks],
        }

    async def hybrid_search(
        self, db: AsyncSession, resume_id, query_embedding, query_text: str, top_k=10
    ) -> list[dict]:
        stored = await self.get_by_resume(db, resume_id)
        docs = stored.get("documents", [])
        vecs = stored.get("embeddings", [])
        metadatas = stored.get("metadatas", [])

        if not docs or not vecs:
            return []

        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        bm25 = self._bm25_indices.get(rid)
        vector_scores = cosine_similarity([query_embedding], vecs)[0]
        bm25_scores_raw = bm25.search(query_text, top_k=len(docs)) if bm25 else []

        bm25_score_map = {idx: score for idx, score in bm25_scores_raw}
        max_bm25 = max(bm25_score_map.values()) if bm25_score_map else 1

        results = []
        for i in range(len(docs)):
            vs = float(vector_scores[i])
            bs = bm25_score_map.get(i, 0) / max_bm25 if max_bm25 > 0 else 0
            hybrid = (VECTOR_WEIGHT * vs) + (BM25_WEIGHT * bs)
            meta = metadatas[i] if i < len(metadatas) else {}
            results.append({
                "index": i,
                "text": docs[i],
                "vector_score": round(vs, 4),
                "bm25_score": round(bs, 4),
                "hybrid_score": round(hybrid, 4),
                "skills": meta.get("skills", ""),
                "section": meta.get("section", ""),
                "chunk_index": meta.get("chunk_index", i),
            })

        results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        return results[:top_k]

    async def query_by_resume(self, db: AsyncSession, resume_id, query_embedding, top_k=5, exclude_section: str | None = "github"):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        distance_col = ResumeChunk.embedding.cosine_distance(query_embedding).label("distance")
        query = select(ResumeChunk, distance_col).where(ResumeChunk.resume_id == rid)
        if exclude_section:
            query = query.where(ResumeChunk.section != exclude_section)
        result = await db.execute(query.order_by(distance_col).limit(top_k))
        rows = result.all()
        if not rows:
            return {"documents": [], "distances": [], "metadatas": []}

        return {
            "documents": [[row[0].text for row in rows]],
            "distances": [[float(row[1]) for row in rows]],
            "metadatas": [[{"skills": row[0].skills or "", "chunk_index": row[0].chunk_index} for row in rows]],
        }

    async def get_resume_text(self, db: AsyncSession, resume_id, exclude_section: str | None = "github") -> str:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        query = select(ResumeChunk).where(ResumeChunk.resume_id == rid)
        if exclude_section:
            query = query.where(ResumeChunk.section != exclude_section)
        result = await db.execute(query.order_by(ResumeChunk.chunk_index))
        chunks = result.scalars().all()
        if not chunks:
            return ""
        return " ".join(c.text for c in chunks if c.text)

    async def delete_by_resume(self, db: AsyncSession, resume_id) -> int:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(delete(ResumeChunk).where(ResumeChunk.resume_id == rid))
        await db.flush()
        self._bm25_indices.pop(rid, None)
        return result.rowcount


vector_store = VectorStoreService()
