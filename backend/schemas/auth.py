from pydantic import BaseModel
from uuid import UUID


class AuthResponse(BaseModel):
    token: str
    user_id: UUID
    email: str
