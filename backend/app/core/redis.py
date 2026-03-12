import redis.asyncio as aioredis
import json
from typing import Optional
from app.core.config import get_settings

settings = get_settings()

redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    global redis_client
    if redis_client is None:
        redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return redis_client


async def cache_get(key: str) -> Optional[dict]:
    r = await get_redis()
    data = await r.get(key)
    if data:
        return json.loads(data)
    return None


async def cache_set(key: str, value: dict, ttl: int = 60):
    r = await get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl)


async def cache_delete(key: str):
    r = await get_redis()
    await r.delete(key)
