import hmac
import logging
import random
import string

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from core.security import create_access_token
from services.database import get_db
from services.redis import get_redis
from services.integrations.brevo import brevo_email
from models.user import User
from schemas.auth import AuthResponse, RequestOTPRequest, VerifyOTPRequest, MessageResponse
from config.constants import RATE_LIMIT_WINDOW_SECONDS, JWT_TOKEN_TTL_SECONDS
from config.settings import settings

logger = logging.getLogger(__name__)
router = APIRouter()

OTP_LENGTH = 6
OTP_TTL_SECONDS = 300
OTP_RATE_LIMIT_MAX = 3
ANON_RATE_LIMIT_MAX = 5
ANON_RATE_LIMIT_WINDOW = 3600


def _generate_otp() -> str:
    return "".join(random.choices(string.digits, k=OTP_LENGTH))


@router.post("/auth/request-otp", response_model=MessageResponse)
async def request_otp(
    body: RequestOTPRequest,
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    normalized_email = body.email.strip().lower()

    rate_key = f"otp_rate:{normalized_email}"
    pipe = redis.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, RATE_LIMIT_WINDOW_SECONDS)
    results = await pipe.exec()
    count = results[0]
    if count > OTP_RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many OTP requests. Please try again later.",
        )

    otp = _generate_otp()
    otp_key = f"otp:{normalized_email}"
    await redis.setex(otp_key, OTP_TTL_SECONDS, otp)

    sent = await brevo_email.send_otp(normalized_email, otp)
    if not sent:
        logger.error(f"Failed to send OTP email to {normalized_email}")

    logger.info(f"OTP sent to {normalized_email}")
    return MessageResponse(message="Verification code sent to your email.")


@router.post("/auth/verify-otp", response_model=AuthResponse)
async def verify_otp(
    body: VerifyOTPRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    redis = await get_redis()

    normalized_email = body.email.strip().lower()
    otp_key = f"otp:{normalized_email}"
    stored_otp = await redis.get(otp_key)

    if not stored_otp:
        raise HTTPException(status_code=400, detail="OTP expired or not found. Please request a new code.")

    if not hmac.compare_digest(body.otp, stored_otp):
        raise HTTPException(status_code=400, detail="Invalid verification code.")

    await redis.delete(otp_key)

    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalar_one_or_none()

    if not user:
        user = User(email=normalized_email)
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except IntegrityError:
            await db.rollback()
            result = await db.execute(select(User).where(User.email == normalized_email))
            user = result.scalar_one()
        logger.info(f"New user created: {normalized_email}")
    else:
        logger.info(f"Existing user logged in: {normalized_email}")

    token = create_access_token(str(user.id), user.email)
    response.set_cookie(
        key="auth_token",
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        max_age=JWT_TOKEN_TTL_SECONDS,
        path="/",
    )
    return AuthResponse(token=token, user_id=user.id, email=user.email)


@router.post("/auth/anonymous", response_model=AuthResponse)
async def anonymous_login(response: Response, db: AsyncSession = Depends(get_db)):
    import uuid

    redis = await get_redis()
    rate_key = "anon_rate:global"
    pipe = redis.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, ANON_RATE_LIMIT_WINDOW)
    results = await pipe.exec()
    count = results[0]
    if count > ANON_RATE_LIMIT_MAX:
        raise HTTPException(status_code=429, detail="Too many anonymous sessions. Please sign in.")

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
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
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
    response.delete_cookie(
        "auth_token",
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
    )
    return {"message": "Logged out"}
