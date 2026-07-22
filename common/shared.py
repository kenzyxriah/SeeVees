from httpx import AsyncClient
import redis.asyncio as redis
from typing import Optional

http_client: Optional[AsyncClient] = None
redis_client: Optional[redis.Redis] = None