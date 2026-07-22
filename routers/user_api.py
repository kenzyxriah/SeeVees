from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
from typing import Optional

from common.api_response import generate_response, generate_error_response
from common.logger import logger
from core.database import get_db
from core.auth import get_current_user, User
from services.user_service import get_user_profile, update_user_profile


router = APIRouter(prefix="/api/v1/users", tags=["Users"])


class UpdateProfileRequest(BaseModel):
    password: Optional[str] = Field(None, min_length=6)
    username: Optional[str] = Field(None, min_length=3, max_length=30)
    first_name: Optional[str] = Field(None, min_length=1, max_length=30)
    last_name: Optional[str] = Field(None, min_length=1, max_length=30)

    class Config:
        extra = "forbid"


@router.get("/profile")
async def view_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve the profile details of the currently authenticated user.
    """
    try:
        profile_data = await get_user_profile(db=db, user_id=current_user.user_id)
        return generate_response(
            succeeded=True,
            entity=profile_data,
            message="User profile retrieved successfully"
        )
    except HTTPException as e:
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred while fetching user profile.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve profile due to a server error"
        )


@router.patch("/profile")
async def patch_profile(
    request: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Partially update the profile details of the currently authenticated user.
    """
    try:
        profile_data = await update_user_profile(
            db=db,
            user_id=current_user.user_id,
            password=request.password,
            username=request.username,
            first_name=request.first_name,
            last_name=request.last_name
        )
        return generate_response(
            succeeded=True,
            entity=profile_data,
            message="User profile updated successfully"
        )
    except HTTPException as e:
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred while updating user profile.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not update profile due to a server error"
        )
