import traceback
from fastapi import Request, status
from fastapi.exceptions import HTTPException as StarletteHTTPException

from common.logger import logger
from common.api_response import generate_error_response
from core.config import ENVIRONMENT


async def global_exception_handler(request: Request, exc: Exception):
    """
    Global safety-net exception handler for unhandled exceptions in routes.

    Args:
        request (Request): Incoming FastAPI HTTP request.
        exc (Exception): The raised exception.

    Returns:
        JSONResponse: Standardized error response payload.
    """
    status_code = 500

    if isinstance(exc, StarletteHTTPException):
        status_code = exc.status_code
        detail_msg = exc.detail if hasattr(exc, "detail") else str(exc)
    else:
        detail_msg = "Internal server error"

    error_trace = "".join(traceback.format_exception(exc))

    msg = f"Environment: {ENVIRONMENT}\nMethod: {request.method}\nURL: {request.url}\nError: {status_code}\n\n{error_trace}"

    logger.error(msg)

    return generate_error_response(
        exception_error=str(detail_msg),
        status_code=status_code,
        message=str(detail_msg)
    )
