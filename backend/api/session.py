import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.storage import vector_store, session_store
from models.resume import MasterResume

logger = logging.getLogger(__name__)
router = APIRouter()


async def _verify_resume_owner(resume_id: str, user_id: UUID, db: AsyncSession) -> bool:
    result = await db.execute(
        select(MasterResume.id).where(
            MasterResume.id == resume_id,
            MasterResume.user_id == user_id,
        )
    )
    return result.scalar_one_or_none() is not None


@router.delete("/session/{resume_id}")
async def delete_session(
    resume_id: str,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await _verify_resume_owner(resume_id, user_id, db):
        raise HTTPException(status_code=404, detail="Resume not found")

    deleted = await vector_store.delete_by_resume(db, resume_id)
    await db.commit()
    await session_store.delete_session(resume_id)
    logger.info(f"Session {resume_id}: deleted {deleted} chunks")
    return {"deleted_chunks": deleted, "session_deleted": True}


@router.delete("/session/end/{resume_id}")
async def end_session(
    resume_id: str,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not await _verify_resume_owner(resume_id, user_id, db):
        raise HTTPException(status_code=404, detail="Resume not found")

    deleted = await vector_store.delete_by_resume(db, resume_id)
    await db.commit()
    await session_store.delete_session(resume_id)
    logger.info(f"Session {resume_id}: ended, deleted {deleted} chunks")
    return {"deleted_chunks": deleted, "session_deleted": True}
