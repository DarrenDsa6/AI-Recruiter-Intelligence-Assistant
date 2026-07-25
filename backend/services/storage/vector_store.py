import logging
from uuid import UUID

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import ResumeChunk
from models.resume import MasterResume
from config.constants import CHUNK_SIZE, CHUNK_OVERLAP

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
            source = metadatas[i].get("source", "resume") if metadatas and i < len(metadatas) else "resume"
            meta = metadatas[i] if metadatas and i < len(metadatas) else {}
            chunk = ResumeChunk(
                resume_id=UUID(resume_id) if isinstance(resume_id, str) else resume_id,
                chunk_index=i,
                chunk_start_char=meta.get("chunk_start", 0),
                chunk_end_char=meta.get("chunk_end", 0),
                text=documents[i] if source == "github" else "",
                embedding=embeddings[i],
                skills=None,
            )
            chunks.append(chunk)

        db.add_all(chunks)
        await db.flush()
        return resume_id

    def _reconstruct_text(self, raw_text: str, chunk_start: int, chunk_end: int) -> str:
        return raw_text[chunk_start:chunk_end]

    async def _get_raw_text(self, db: AsyncSession, resume_id) -> str | None:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(MasterResume.raw_text).where(MasterResume.id == rid)
        )
        return result.scalar_one_or_none()

    async def get_by_resume(self, db: AsyncSession, resume_id):
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(ResumeChunk).where(ResumeChunk.resume_id == rid).order_by(ResumeChunk.chunk_index)
        )
        chunks = result.scalars().all()
        if not chunks:
            return {"documents": [], "embeddings": [], "metadatas": []}

        raw_text = await self._get_raw_text(db, resume_id)

        documents = []
        for c in chunks:
            if c.text:
                documents.append(c.text)
            elif raw_text and c.chunk_start_char is not None and c.chunk_end_char is not None:
                documents.append(self._reconstruct_text(raw_text, c.chunk_start_char, c.chunk_end_char))
            else:
                documents.append("")

        return {
            "documents": documents,
            "embeddings": [list(c.embedding) for c in chunks],
            "metadatas": [{"skills": c.skills or "", "chunk_index": c.chunk_index} for c in chunks],
        }

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

        raw_text = await self._get_raw_text(db, resume_id)

        documents = []
        for c in chunks:
            if c.text:
                documents.append(c.text)
            elif raw_text and c.chunk_start_char is not None and c.chunk_end_char is not None:
                documents.append(self._reconstruct_text(raw_text, c.chunk_start_char, c.chunk_end_char))
            else:
                documents.append("")

        return {
            "documents": [documents],
            "distances": [[0.0 for _ in chunks]],
            "metadatas": [[{"skills": c.skills or "", "chunk_index": c.chunk_index} for c in chunks]],
        }

    async def get_resume_text(self, db: AsyncSession, resume_id) -> str:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(
            select(ResumeChunk).where(ResumeChunk.resume_id == rid).order_by(ResumeChunk.chunk_index)
        )
        chunks = result.scalars().all()
        if not chunks:
            return ""

        raw_text = await self._get_raw_text(db, resume_id)
        if raw_text:
            return raw_text

        return " ".join(c.text for c in chunks if c.text)

    async def delete_by_resume(self, db: AsyncSession, resume_id) -> int:
        rid = UUID(resume_id) if isinstance(resume_id, str) else resume_id
        result = await db.execute(delete(ResumeChunk).where(ResumeChunk.resume_id == rid))
        return result.rowcount


vector_store = VectorStoreService()
