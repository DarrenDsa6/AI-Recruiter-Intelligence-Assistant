import logging
from uuid import UUID

from sqlalchemy import select, func, delete, text
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import ResumeChunk
from services.db import async_session_factory

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
            skills = None
            if metadatas and i < len(metadatas) and "skills" in metadatas[i]:
                skills = metadatas[i]["skills"]
            chunk = ResumeChunk(
                resume_id=UUID(resume_id) if isinstance(resume_id, str) else resume_id,
                chunk_index=i,
                text=documents[i],
                embedding=embeddings[i],
                skills=skills,
            )
            chunks.append(chunk)

        db.add_all(chunks)
        await db.flush()
        return resume_id

    async def get_by_resume(self, db: AsyncSession, resume_id):
        result = await db.execute(
            select(ResumeChunk)
            .where(ResumeChunk.resume_id == UUID(resume_id) if isinstance(resume_id, str) else ResumeChunk.resume_id == resume_id)
            .order_by(ResumeChunk.chunk_index)
        )
        chunks = result.scalars().all()
        if not chunks:
            return {"documents": [], "embeddings": [], "metadatas": []}

        documents = [c.text for c in chunks]
        embeddings = [list(c.embedding) for c in chunks]
        metadatas = [{"skills": c.skills or "", "chunk_index": c.chunk_index} for c in chunks]

        return {"documents": documents, "embeddings": embeddings, "metadatas": metadatas}

    async def query_by_resume(self, db: AsyncSession, resume_id, query_embedding, top_k=5):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(ResumeChunk)
            .where(ResumeChunk.resume_id == rid)
            .order_by(ResumeChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        chunks = result.scalars().all()
        if not chunks:
            return {"documents": [], "distances": [], "metadatas": []}

        documents = [[c.text for c in chunks]]
        distances = [[0.0 for _ in chunks]]  # pgvector doesn't return distances by default
        metadatas = [[{"skills": c.skills or "", "chunk_index": c.chunk_index} for c in chunks]]

        return {"documents": documents, "distances": distances, "metadatas": metadatas}

    async def get_resume_text(self, db: AsyncSession, resume_id):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(ResumeChunk.text)
            .where(ResumeChunk.resume_id == rid)
            .order_by(ResumeChunk.chunk_index)
        )
        texts = [row[0] for row in result.all()]
        return " ".join(texts) if texts else ""

    async def delete_by_resume(self, db: AsyncSession, resume_id):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            delete(ResumeChunk).where(ResumeChunk.resume_id == rid)
        )
        return result.rowcount


vector_store = VectorStoreService()
