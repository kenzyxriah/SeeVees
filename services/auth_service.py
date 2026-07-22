from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from common.logger import logger
from common.crypto import Crypto
from models.user import User, RoleEnum
from core.auth import fetch_token


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    role: RoleEnum,
) -> dict[str, str]:
    """
    Register a new user in the database and automatically logs them in.

    Args:
        db (AsyncSession): Database session.
        email (str): User's email address.
        password (str): Plaintext password.
        first_name (str): First name.
        last_name (str): Last name.
        role (RoleEnum): User role (ADMIN, EMPLOYER).

    Returns:
        dict[str, str]: Dictionary containing access_token and token_type.

    Raises:
        ValueError: If email is already registered.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        logger.warning(f"Registration failed: Email {email} already exists")
        raise HTTPException(status_code=400,detail="User with this email already exists")

    hashed_pwd = Crypto.hash_password(password)
    user = User(
        email=email,
        password_hash=hashed_pwd,
        first_name=first_name,
        last_name=last_name,
        role=role,
        username=None
    )

    db.add(user)
    await db.flush()
    await db.refresh(user)
    token = await fetch_token(user_id=str(user.id), role=user.role, email=user.email)
    logger.info(f"User registered successfully and logged in: {user.email} with role {user.role}")

    return {"access_token": token, "token_type": "bearer"}




async def authenticate_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> dict[str, str]:
    """
    Authenticate a user by email and password, returning an access token.

    Args:
        db (AsyncSession): Database session.
        email (str): User's email address.
        password (str): Plaintext password.

    Returns:
        dict[str, str]: Dictionary containing access_token and token_type.

    Raises:
        ValueError: If authentication fails due to invalid credentials.
    """
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not Crypto.verify_password(password, user.password_hash):
        logger.error(f"Failed login attempt for email: {email}")
        raise HTTPException(status_code=401,detail="Invalid email or password")

    token = await fetch_token(user_id=str(user.id), role=user.role, email=user.email)
    logger.info(f"User authenticated successfully: {user.email}")

    return {"access_token": token, "token_type": "bearer"}
