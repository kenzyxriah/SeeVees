from contextlib import asynccontextmanager
from httpx import AsyncClient, Limits
import redis.asyncio as redis
from fastapi import FastAPI

from common import shared
from common.logger import logger
from core.config import REDIS_URL
from core.database import engine, Base
import models  


@asynccontextmanager
async def lifespan(app: FastAPI):
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("PostgreSQL database tables verified/created")

    shared.http_client = AsyncClient(
        timeout=120.0,
        limits=Limits(
            max_connections=1000,
            max_keepalive_connections=200,
            keepalive_expiry=30.0,
        ),
    )
    if shared.http_client:
        logger.info("Connection pooling for httpx calls are live")

    shared.redis_client = redis.from_url(
        REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
    )
    logger.info("Redis connection pool live")

    yield

    if shared.http_client:
        await shared.http_client.aclose()
    if shared.redis_client:
        await shared.redis_client.aclose()
