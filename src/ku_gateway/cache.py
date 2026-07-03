"""Redis caching for decay scores."""

import json
from typing import Optional, Any
import redis.asyncio as redis
from .config import Settings
from .telemetry import logger

settings = Settings()

class Cache:
    """Redis cache for decay scores."""
    
    def __init__(self):
        self.enabled = settings.redis_enabled
        if self.enabled:
            try:
                self.client = redis.from_url(settings.redis_url)
                logger.info("Redis cache enabled")
            except Exception as e:
                logger.error(f"Redis connection failed: {e}")
                self.enabled = False
    
    async def get(self, key: str) -> Optional[dict]:
        """Get cached value."""
        if not self.enabled:
            return None
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.debug(f"Cache get error: {e}")
        return None
    
    async def set(self, key: str, value: dict, ttl: int = 3600):
        """Set cached value."""
        if not self.enabled:
            return
        try:
            await self.client.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception as e:
            logger.debug(f"Cache set error: {e}")
    
    async def clear(self, pattern: str = "*"):
        """Clear cache."""
        if not self.enabled:
            return
        try:
            keys = await self.client.keys(pattern)
            if keys:
                await self.client.delete(*keys)
        except Exception as e:
            logger.debug(f"Cache clear error: {e}")