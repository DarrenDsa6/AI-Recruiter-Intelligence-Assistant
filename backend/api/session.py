import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from services.database import get_db
from services.storage import vector_store, session_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await vector_store.delete_by_resume(db, session_id)
    await session_store.delete_session(session_id)
    logger.info(f"Session {session_id}: deleted {deleted} chunks")
    return {"deleted_chunks": deleted, "session_deleted": True}


@router.delete("/session/end/{session_id}")
async def end_session(session_id: str, db: AsyncSession = Depends(get_db)):
    deleted = await vector_store.delete_by_resume(db, session_id)
    await session_store.delete_session(session_id)
    logger.info(f"Session {session_id}: ended, deleted {deleted} chunks")
    return {"deleted_chunks": deleted, "session_deleted": True}
