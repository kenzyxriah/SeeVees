import jwt
from fastapi import Request
from fastapi.responses import JSONResponse

from common.logger import logger
from common import shared
from core.auth import SECRET_KEY


def create_error_response(status_code: int, message: str) -> JSONResponse:
    """
    Construct a standardized JSON error response.

    Args:
        status_code (int): HTTP status code.
        message (str): Error message description.

    Returns:
        JSONResponse: Formatted JSON response with status code and error payload.
    """
    return JSONResponse(status_code=status_code, content={"succeeded": False, "message": message})


async def check_global_rate_limit(key: str, limit: int = 50, window: int = 60) -> bool:
    """
    Check if a Redis sliding window rate limit key has exceeded the allowed request count.

    Args:
        key (str): Redis cache key for rate limiting.
        limit (int, optional): Maximum requests allowed in window. Defaults to 50.
        window (int, optional): Window size in seconds. Defaults to 60.

    Returns:
        bool: True if rate limit is exceeded, False otherwise.
    """
    if not shared.redis_client:
        return False
    requests_count = await shared.redis_client.incr(key)
    if requests_count == 1:
        await shared.redis_client.expire(key, window)
    return requests_count > limit


async def monitor_traffic(request: Request, call_next):
    """
    Middleware function that enforces global user rate limiting on incoming HTTP requests.

    Args:
        request (Request): Incoming FastAPI HTTP request.
        call_next (Callable): Next middleware/route handler function in execution pipeline.

    Returns:
        Response: HTTP response object.
    """
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            token = auth_header.removeprefix("Bearer ").strip()
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id = payload.get("user_id")
        except Exception:
            pass

    if user_id and await check_global_rate_limit(f"global_rate_limit:user:{user_id}"):
        logger.warning(f"Global user rate limit exceeded for: {user_id}")
        return create_error_response(429, "Global rate limit exceeded. Please slow down.")

    return await call_next(request)

