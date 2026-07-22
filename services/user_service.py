import uuid
from typing import Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from common.logger import logger
from common.crypto import Crypto
from models.user import User


def format_profile(user: User) -> dict[str, Any]:
    """
    Format a User database model instance into a clean profile dictionary.

    Args:
        user (User): The SQLAlchemy User model instance.

    Returns:
        dict[str, Any]: Profile dictionary excluding user ID and formatted created_at timestamp.
    """
    return {
        "email": user.email,
        "username": user.username,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "role": user.role,
        "created_at": user.created_at.strftime("%y-%m-%d %H:%M:%S") if user.created_at else None
    }


async def get_user_profile(db: AsyncSession, user_id: uuid.UUID) -> dict[str, Any]:
    """
    Retrieve and format the profile details of a user by their unique user ID.

    Args:
        db (AsyncSession): Database session.
        user_id (uuid.UUID): Unique user UUID.

    Returns:
        dict[str, Any]: Formatted profile dictionary of the user.

    Raises:
        ValueError: If the user does not exist in the database.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        logger.warning(f"Profile fetch failed: User {user_id} not found")
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    return format_profile(user)


async def update_user_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    password: Optional[str] = None,
    username: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None
) -> dict[str, Any]:
    """
    Update profile details for a given user ID.

    Args:
        db (AsyncSession): Database session.
        user_id (uuid.UUID): Unique user UUID.
        password (Optional[str], optional): New plaintext password to hash and set.
        username (Optional[str], optional): New username. Enforces uniqueness.
        first_name (Optional[str], optional): New first name.
        last_name (Optional[str], optional): New last name.

    Returns:
        dict[str, Any]: The updated and formatted profile dictionary.

    Raises:
        ValueError: If the user is not found or the new username is already taken.
    """
    stmt = select(User).where(User.id == user_id)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()


    if not user:
        logger.warning(f"Profile update failed: User {user_id} not found")
        raise HTTPException(
            status_code=404,
            detail="User profile not found"
        )

    if username is not None and username != user.username:
        username_check = select(User).where(User.username == username)
        check_result = await db.execute(username_check)
        if check_result.scalar_one_or_none():
            logger.warning(f"Profile update failed: Username '{username}' already taken")
            raise HTTPException(
                status_code=400,
                detail="Username already taken"
            )
        user.username = username

    if password is not None:
        user.password_hash = Crypto.hash_password(password)

    if first_name is not None:
        user.first_name = first_name

    if last_name is not None:
        user.last_name = last_name

    db.add(user)
    await db.flush()

    logger.info(f"User profile updated successfully: {user.email}")
    return format_profile(user)

