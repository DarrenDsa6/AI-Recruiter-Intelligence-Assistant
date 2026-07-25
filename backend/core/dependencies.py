from uuid import UUID

import jwt
from fastapi import Cookie, Header, HTTPException, Request

from core.security import decode_access_token


async def get_current_user(
    request: Request,
    authorization: str = Header(None),
) -> UUID:
    token = None

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "")
    elif "auth_token" in request.cookies:
        token = request.cookies["auth_token"]

    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = decode_access_token(token)
        return UUID(payload["sub"])
    except (KeyError, ValueError, jwt.exceptions.PyJWTError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
