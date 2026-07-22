from datetime import datetime, timedelta, timezone
from typing import Optional, Literal, get_args
from pydantic import BaseModel
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt, uuid

from core.config import SECRET_KEY
from common import shared
from common.logger import logger

security = HTTPBearer()

Role = Literal["ADMIN", "EMPLOYER"]


class User(BaseModel):
    user_id: uuid.UUID
    role: Role
    email: str



async def fetch_token(
    user_id: str,
    role: Role,
    email: str
) -> str:
    """
    Retrieve an active access token from Redis cache or generate and cache a new JWT.

    Args:
        user_id (str): Unique user identifier.
        role (Role): User role string ('ADMIN', 'EMPLOYER').
        email (str): User's email address.

    Returns:
        str: Encoded JWT access token.
    """
    key = f"token:{user_id}"
    cached_token = await shared.redis_client.get(key)
    if cached_token:
        return cached_token

    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=60)
    payload = {"user_id": user_id, "role": role, "exp": expire, "iat": now, "email": email}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    await shared.redis_client.set(key, token, ex=3600)

    return token


async def get_dev_token(user_id: str = "dev_user_1", role: Role = "ADMIN", email: str = "dev@example.com") -> str:
    return await fetch_token(user_id=user_id, role=role, email=email)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    FastAPI dependency that decodes the HTTP Bearer token and returns the current user context.

    Args:
        credentials (HTTPAuthorizationCredentials): Authorization header credentials.

    Returns:
        User: Authenticated User model instance.

    Raises:
        HTTPException: If token is missing, expired, or invalid.
    """
    try:
        token = credentials.credentials.removeprefix("Bearer ").strip()

        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=["HS256"]
        )

        user_id: str = payload.get("user_id")
        if not user_id or not isinstance(user_id, str):
            raise HTTPException(status_code=401, detail="Invalid token: missing user_id")

        role: str = payload.get("role")
        if not role or role not in get_args(Role):
            raise HTTPException(status_code=401, detail="Invalid token: missing or invalid role")

        email: str = payload.get("email")
        if not email or not isinstance(email, str):
            raise HTTPException(status_code=401, detail="Invalid token: missing or invalid email")

        return User(
            user_id=user_id,
            role=role,
            email=email
        )

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {e}")


def require_role(allowed_roles: list[Role]):
    """
    FastAPI dependency factory that restricts endpoint access based on user roles.

    Args:
        allowed_roles (list[Role]): Permitted role values allowed to access the endpoint.

    Returns:
        Callable: Dependency function verifying current user role against allowed roles.
    """
    def dependency(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="Forbidden: Insufficient role permissions")
        return current_user

    return dependency



