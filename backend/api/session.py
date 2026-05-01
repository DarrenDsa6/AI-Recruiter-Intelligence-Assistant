from fastapi import APIRouter

from services.vector_store import VectorStoreService
from services.session_store import SessionStore

router = APIRouter()

vector_store = VectorStoreService()
session_store = SessionStore()


@router.delete("/session/{session_id}")
async def delete_session(session_id: str):
    deleted = vector_store.delete_by_session(session_id)
    session_store.delete_session(session_id)

    return {
        "deleted_chunks": deleted,
        "session_deleted": True
    }