import logging
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import ResumeChunk

logger = logging.getLogger(__name__)


class VectorStoreService:
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
            )
            chunks.append(chunk)

        db.add_all(chunks)
        await db.flush()
        return resume_id

    async def get_by_resume(self, db: AsyncSession, resume_id):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(ResumeChunk).where(ResumeChunk.resume_id == rid).order_by(ResumeChunk.chunk_index)
        )
        chunks = result.scalars().all()
        if not chunks:
            return {"documents": [], "embeddings": [], "metadatas": []}

        return {
            "documents": [c.text for c in chunks],
            "embeddings": [list(c.embedding) for c in chunks],
            "metadatas": [{"skills": c.skills or "", "chunk_index": c.chunk_index} for c in chunks],
        }

    async def query_by_resume(self, db: AsyncSession, resume_id, query_embedding, top_k=5):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        distance_col = ResumeChunk.embedding.cosine_distance(query_embedding).label("distance")
        result = await db.execute(
            select(ResumeChunk, distance_col)
            .where(ResumeChunk.resume_id == rid)
            .order_by(distance_col)
            .limit(top_k)
        )
        rows = result.all()
        if not rows:
            return {"documents": [], "distances": [], "metadatas": []}

        return {
            "documents": [[row[0].text for row in rows]],
            "distances": [[float(row[1]) for row in rows]],
            "metadatas": [[{"skills": row[0].skills or "", "chunk_index": row[0].chunk_index} for row in rows]],
        }

    async def get_resume_text(self, db: AsyncSession, resume_id) -> str:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(ResumeChunk).where(ResumeChunk.resume_id == rid).order_by(ResumeChunk.chunk_index)
        )
        chunks = result.scalars().all()
        if not chunks:
            return ""
        return " ".join(c.text for c in chunks if c.text)

    async def delete_by_resume(self, db: AsyncSession, resume_id) -> int:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(delete(ResumeChunk).where(ResumeChunk.resume_id == rid))
        await db.flush()
        return result.rowcount


vector_store = VectorStoreService()
