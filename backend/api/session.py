from fastapi import APIRouter
import logging

from services.vector_store import vector_store
from services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    deleted = vector_store.delete_by_session(session_id)
    session_store.delete_session(session_id)
    logger.info(f"Session {session_id}: deleted {deleted} chunks")

    return {
        "deleted_chunks": deleted,
        "session_deleted": True
    }


@router.delete("/session/end/{session_id}")
async def end_session(session_id: str):
    deleted = vector_store.delete_by_session(session_id)
    session_store.delete_session(session_id)
    logger.info(f"Session {session_id}: ended, deleted {deleted} chunks")

    return {
        "deleted_chunks": deleted,
        "session_deleted": True
    }
