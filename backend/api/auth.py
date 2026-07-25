import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from core.security import create_access_token
from services.database import get_db
from models.user import User
from schemas.auth import AuthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/auth/anonymous", response_model=AuthResponse)
async def anonymous_login(db: AsyncSession = Depends(get_db)):
    import uuid

    email = f"anon-{uuid.uuid4().hex[:12]}@local.dev"

    user = User(email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.email)
    logger.info(f"Anonymous user created: {user.email}")

    return AuthResponse(token=token, user_id=user.id, email=user.email)
