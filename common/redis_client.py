import json
from common import shared
from common.logger import logger
import redis.asyncio as redis

async def get_session(session_id: str):
    if not shared.redis_client:
        logger.warning("Redis client not initialized")
        return 0, None

    try:
        session_data = await shared.redis_client.get(f"session:{session_id}")
        if not session_data:
            return 0, None
        msgs = json.loads(session_data)
        return len(msgs), msgs
    except redis.RedisError as e:
        logger.error(f"Redis error in get_session: {e}")
        return 0, None



async def set_session(session_id: str, history: list, ex: int = None):
    if not shared.redis_client:
        logger.warning("Redis client not initialized")
        return
    try:
        await shared.redis_client.set(f"session:{session_id}", json.dumps(history),
                                     ex = ex)
    except redis.RedisError as e:
        logger.error(f"Redis error in set_session: {e}")


async def delete_session(session_id: str):
    if not shared.redis_client:
        logger.warning("Redis client not initialized")
        return
    try:
        await shared.redis_client.delete(f"session:{session_id}")
    except redis.RedisError as e:
        logger.error(f"Redis error in delete_session: {e}")
