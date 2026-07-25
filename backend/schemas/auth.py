from pydantic import BaseModel, EmailStr
from uuid import UUID

from schemas.common import MessageResponse


class RequestOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class AuthResponse(BaseModel):
    token: str
    user_id: UUID
    email: str
