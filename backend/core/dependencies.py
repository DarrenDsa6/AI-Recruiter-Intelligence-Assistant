from uuid import UUID

import jwt
from fastapi import Header, HTTPException

from core.security import decode_access_token


async def get_current_user(authorization: str = Header(...)) -> UUID:
    try:
        token = authorization.replace("Bearer ", "")
        payload = decode_access_token(token)
        return UUID(payload["sub"])
    except (KeyError, ValueError, jwt.exceptions.PyJWTError):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
