from pydantic import BaseModel, EmailStr, Field
from uuid import UUID


class RequestOTP(BaseModel):
    email: EmailStr


class VerifyOTP(BaseModel):
    email: EmailStr
    code: str = Field(min_length=6, max_length=6)


class AuthResponse(BaseModel):
    token: str
    user_id: UUID
    email: str
