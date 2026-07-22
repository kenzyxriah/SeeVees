from fastapi import APIRouter, Depends, status, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from common.api_response import generate_response, generate_error_response
from common.logger import logger
from core.database import get_db
from core.limiter import limiter
from models.user import RoleEnum
from services.auth_service import register_user, authenticate_user


router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    role: RoleEnum

    class Config:
        extra = "forbid"


class LoginRequest(BaseModel):
    email: str
    password: str

    class Config:
        extra = "forbid"


@router.post("/register")
@limiter.limit("5/minute")
async def register(request: Request, payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """
    Register a new user and automatically log them in, returning an access token.
    """
    try:
        token_data = await register_user(
            db=db,
            email=payload.email,
            password=payload.password,
            first_name=payload.first_name,
            last_name=payload.last_name,
            role=payload.role
        )
        return generate_response(
            succeeded=True,
            entity=token_data,
            message="User registered and logged in successfully"
        )
    except HTTPException as e:
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred during user registration.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not complete registration due to a server error"
        )


@router.post("/login")
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    """
    Authenticate a user by email and password, returning an access token.
    """
    try:
        token_data = await authenticate_user(
            db=db,
            email=request.email,
            password=request.password
        )
        return generate_response(
            succeeded=True,
            entity=token_data,
            message="User authenticated successfully"
        )
    except HTTPException as e:
        return generate_error_response(
            exception_error=e.detail,
            status_code=e.status_code,
            message=e.detail
        )
    except Exception as e:
        logger.exception("An unexpected error occurred during user authentication.\n")
        return generate_error_response(
            exception_error=str(e),
            status_code=500,
            message="Could not complete login due to a server error"
        )

