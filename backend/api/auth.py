import logging
import random
import string

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from core.security import create_access_token
from services.database import get_db
from services.redis import get_redis
from services.integrations.brevo import brevo_email
from models.user import User
from schemas.auth import AuthResponse, RequestOTPRequest, VerifyOTPRequest, MessageResponse
from config.constants import RATE_LIMIT_WINDOW_SECONDS, JWT_TOKEN_TTL_SECONDS

logger = logging.getLogger(__name__)
router = APIRouter()

OTP_LENGTH = 6
OTP_TTL_SECONDS = 300
OTP_RATE_LIMIT_MAX = 3


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


@router.post("/auth/request-otp", response_model=MessageResponse)
async def request_otp(
    body: RequestOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    rate_key = f"otp_rate:{body.email}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, RATE_LIMIT_WINDOW_SECONDS)
    if count > OTP_RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try again later.",
        )

    otp = _generate_otp()
    otp_key = f"otp:{body.email}"
    await redis.setex(otp_key, OTP_TTL_SECONDS, otp)

    sent = await brevo_email.send_otp(body.email, otp)
    if not sent:
        logger.error(f"Failed to send OTP email to {body.email}")

    logger.info(f"OTP sent to {body.email}")
    return MessageResponse(message="Verification code sent to your email.")


@router.post("/auth/verify-otp", response_model=AuthResponse)
async def verify_otp(
    body: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    otp_key = f"otp:{body.email}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Please request a new code.")

    if body.otp != stored_otp:
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    await redis.delete(otp_key)

    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=body.email)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        logger.info(f"New user created: {body.email}")
    else:
        logger.info(f"Existing user logged in: {body.email}")

    token = create_access_token(str(user.id), user.email)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=JWT_TOKEN_TTL_SECONDS,
        path="/",
    )
    return AuthResponse(token=token, user_id=user.id, email=user.email)


@router.post("/auth/anonymous", response_model=AuthResponse)
async def anonymous_login(response: Response, db: AsyncSession = Depends(get_db)):
    import uuid

    email = f"anon-{uuid.uuid4().hex[:12]}@local.dev"

    user = User(email=email)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id), user.email)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=True,
        samesite="strict",
        max_age=JWT_TOKEN_TTL_SECONDS,
        path="/",
    )
    logger.info(f"Anonymous user created: {user.email}")

    return AuthResponse(token=token, user_id=user.id, email=user.email)


@router.get("/auth/me")
async def get_me(user_id=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return {"user_id": user.id, "email": user.email}


@router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("auth_token", path="/")
    return {"message": "Logged out"}
