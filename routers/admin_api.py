from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from common.api_response import generate_response, generate_error_response
from common.logger import logger
from core.database import get_db
from core.auth import require_role, User
from services.retrieve_service import get_all_tests, get_all_submissions


router = APIRouter(prefix="/api/v1/admin", tags=["Retrieval"])


@router.get("/tests")
async def fetch_admin_tests(
    start: int = Query(0, ge=0),
    limit: int = Query(30, ge=1, le=100),
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to retrieve all technical tests on the platform.
    """
    try:
        data = await get_all_tests(db=db, employer_id=None, start=start, limit=limit)
        return generate_response(entity=data, message="All tests retrieved successfully")
        
    except Exception as e:
        logger.exception("An unexpected error occurred during admin tests retrieval.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve tests due to a server error"
        )


@router.get("/submissions")
async def fetch_admin_submissions(
    start: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_role(["ADMIN"])),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin-only endpoint to retrieve all candidate test submissions on the platform.
    """
    try:
        data = await get_all_submissions(db=db, employer_id=None, start=start, limit=limit)
        return generate_response(entity=data, message="All submissions retrieved successfully")
    except Exception as e:
        logger.exception("An unexpected error occurred during admin submissions retrieval.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not retrieve submissions due to a server error"
        )


