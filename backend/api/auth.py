import random
import os
import logging
from datetime import datetime, timezone

import jwt
from fastapi import APIRouter, Request, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_client import get_redis
from services.db import get_db
from models.user import User
from schemas.auth import RequestOTP, VerifyOTP, AuthResponse
from schemas.common import MessageResponse, ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM = os.environ.get("RESEND_FROM_EMAIL", "")
JWT_SECRET = os.environ.get("JWT_SECRET", "")
JWT_TTL = 3600  # 1 hour


def _generate_otp() -> str:
    return f"{random.randint(0, 999999):06d}"


def _create_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc).timestamp() + JWT_TTL,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


async def _send_otp_email(email: str, code: str):
    import httpx
    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {RESEND_API_KEY}"},
            json={
                "from": RESEND_FROM,
                "to": [email],
                "subject": "Your AI Recruiter Login Code",
                "html": f"""
                <div style="font-family: sans-serif; text-align: center; padding: 40px;">
                    <h2>Your verification code</h2>
                    <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; margin: 20px 0;">
                        {code}
                    </p>
                    <p style="color: #666;">Code expires in 5 minutes.</p>
                </div>
                """,
            },
        )


def _get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/auth/request-otp", response_model=MessageResponse)
async def request_otp(body: RequestOTP, request: Request):
    redis = await get_redis()
    email = body.email.lower().strip()
    ip = _get_client_ip(request)

    # Rate limit: 3 per email per 5 min
    email_key = f"otp_rate:{email}"
    email_count = await redis.incr(email_key)
    if email_count == 1:
        await redis.expire(email_key, 300)
    if email_count > 3:
        return MessageResponse(message="Too many requests. Try again later.")

    # Rate limit: 10 per IP per hour
    ip_key = f"otp_ip:{ip}"
    ip_count = await redis.incr(ip_key)
    if ip_count == 1:
        await redis.expire(ip_key, 3600)
    if ip_count > 10:
        return MessageResponse(message="Too many requests. Try again later.")

    code = _generate_otp()
    await redis.setex(f"otp:{email}", 300, code)

    if RESEND_API_KEY and RESEND_FROM:
        try:
            await _send_otp_email(email, code)
        except Exception as e:
            logger.error(f"Failed to send OTP email: {e}")
            return MessageResponse(message="Failed to send email. Try again.")

    logger.info(f"OTP sent to {email}")
    return MessageResponse(message="OTP sent to your email.")


@router.post("/auth/verify-otp", response_model=AuthResponse)
async def verify_otp(body: VerifyOTP, db: AsyncSession = Depends(get_db)):
    redis = await get_redis()
    email = body.email.lower().strip()

    stored_code = await redis.get(f"otp:{email}")
    if not stored_code:
        return ErrorResponse(error="OTP expired or not found.")
    if stored_code != body.code:
        return ErrorResponse(error="Invalid code.")

    await redis.delete(f"otp:{email}")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if user:
        user.last_login = datetime.now(timezone.utc)
    else:
        user = User(email=email)
        db.add(user)

    await db.commit()
    await db.refresh(user)

    token = _create_token(str(user.id), user.email)
    logger.info(f"User authenticated: {user.email}")

    return AuthResponse(token=token, user_id=user.id, email=user.email)
