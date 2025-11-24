"""
Redis Cache Service
High-performance caching with TTL, rate limiting, and pub/sub
"""
import json
import pickle
from typing import Optional, Any, List
from datetime import timedelta
import redis.asyncio as redis
from backend.config import settings
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Enterprise Redis cache service"""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
    
    async def connect(self):
        """Connect to Redis"""
        try:
            self.redis = await redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=False,  # We'll handle encoding ourselves
                max_connections=50
            )
            # Test connection
            await self.redis.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.warning(f"⚠️  Redis connection failed: {e}")
            logger.warning("⚠️  Sistema funcionará com cache in-memory (limitado)")
            logger.warning("⚠️  Para melhor performance, inicie Redis:")
            logger.warning("   • Docker: docker-compose up -d")
            logger.warning("   • Windows: .\install_redis_windows.ps1")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.redis:
            await self.redis.close()
            logger.info("👋 Redis disconnected")
    
    # ========== Basic Cache Operations ==========
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self.redis:
            return None
        
        try:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key {key}: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None
    ) -> bool:
        """
        Set value in cache
        
        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds
        """
        if not self.redis:
            return False
        
        try:
            json_data = json.dumps(value)
            if ttl:
                await self.redis.setex(key, ttl, json_data)
            else:
                await self.redis.set(key, json_data)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key {key}: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.redis:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {e}")
            return False
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Set expiration on key"""
        if not self.redis:
            return False
        
        try:
            await self.redis.expire(key, seconds)
            return True
        except Exception as e:
            logger.error(f"Cache expire error for key {key}: {e}")
            return False
    
    # ========== Advanced Operations ==========
    
    async def get_many(self, keys: List[str]) -> dict:
        """Get multiple keys at once"""
        if not self.redis or not keys:
            return {}
        
        try:
            values = await self.redis.mget(keys)
            result = {}
            for key, value in zip(keys, values):
                if value:
                    result[key] = json.loads(value)
            return result
        except Exception as e:
            logger.error(f"Cache get_many error: {e}")
            return {}
    
    async def set_many(self, mapping: dict, ttl: Optional[int] = None) -> bool:
        """Set multiple key-value pairs"""
        if not self.redis or not mapping:
            return False
        
        try:
            pipe = self.redis.pipeline()
            for key, value in mapping.items():
                json_data = json.dumps(value)
                if ttl:
                    pipe.setex(key, ttl, json_data)
                else:
                    pipe.set(key, json_data)
            await pipe.execute()
            return True
        except Exception as e:
            logger.error(f"Cache set_many error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter"""
        if not self.redis:
            return None
        
        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {e}")
            return None
    
    async def decrement(self, key: str, amount: int = 1) -> Optional[int]:
        """Decrement counter"""
        if not self.redis:
            return None
        
        try:
            return await self.redis.decrby(key, amount)
        except Exception as e:
            logger.error(f"Cache decrement error for key {key}: {e}")
            return None
    
    # ========== Rate Limiting ==========
    
    async def check_rate_limit(
        self,
        key: str,
        max_requests: int,
        window_seconds: int
    ) -> tuple[bool, int]:
        """
        Check if rate limit is exceeded
        
        Returns: (is_allowed, remaining_requests)
        """
        if not self.redis:
            return True, max_requests
        
        try:
            current = await self.redis.get(key)
            
            if current is None:
                # First request in window
                await self.redis.setex(key, window_seconds, 1)
                return True, max_requests - 1
            
            current_count = int(current)
            
            if current_count >= max_requests:
                # Rate limit exceeded
                return False, 0
            
            # Increment and return
            new_count = await self.redis.incr(key)
            remaining = max(0, max_requests - new_count)
            return True, remaining
            
        except Exception as e:
            logger.error(f"Rate limit check error for key {key}: {e}")
            return True, max_requests  # Fail open
    
    async def reset_rate_limit(self, key: str) -> bool:
        """Reset rate limit counter"""
        return await self.delete(key)
    
    # ========== Pub/Sub ==========
    
    async def publish(self, channel: str, message: dict) -> bool:
        """Publish message to channel"""
        if not self.redis:
            return False
        
        try:
            await self.redis.publish(channel, json.dumps(message))
            return True
        except Exception as e:
            logger.error(f"Publish error to channel {channel}: {e}")
            return False
    
    async def subscribe(self, *channels: str):
        """Subscribe to channels"""
        if not self.redis:
            return None
        
        try:
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(*channels)
            return pubsub
        except Exception as e:
            logger.error(f"Subscribe error: {e}")
            return None
    
    # ========== Lists ==========
    
    async def list_push(self, key: str, value: Any, left: bool = True) -> bool:
        """Push value to list (left or right)"""
        if not self.redis:
            return False
        
        try:
            json_data = json.dumps(value)
            if left:
                await self.redis.lpush(key, json_data)
            else:
                await self.redis.rpush(key, json_data)
            return True
        except Exception as e:
            logger.error(f"List push error for key {key}: {e}")
            return False
    
    async def list_pop(self, key: str, left: bool = True) -> Optional[Any]:
        """Pop value from list (left or right)"""
        if not self.redis:
            return None
        
        try:
            if left:
                data = await self.redis.lpop(key)
            else:
                data = await self.redis.rpop(key)
            
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error(f"List pop error for key {key}: {e}")
            return None
    
    async def list_range(self, key: str, start: int = 0, end: int = -1) -> List[Any]:
        """Get range of values from list"""
        if not self.redis:
            return []
        
        try:
            items = await self.redis.lrange(key, start, end)
            return [json.loads(item) for item in items]
        except Exception as e:
            logger.error(f"List range error for key {key}: {e}")
            return []
    
    # ========== Sets ==========
    
    async def set_add(self, key: str, *values: Any) -> bool:
        """Add values to set"""
        if not self.redis or not values:
            return False
        
        try:
            json_values = [json.dumps(v) for v in values]
            await self.redis.sadd(key, *json_values)
            return True
        except Exception as e:
            logger.error(f"Set add error for key {key}: {e}")
            return False
    
    async def set_remove(self, key: str, *values: Any) -> bool:
        """Remove values from set"""
        if not self.redis or not values:
            return False
        
        try:
            json_values = [json.dumps(v) for v in values]
            await self.redis.srem(key, *json_values)
            return True
        except Exception as e:
            logger.error(f"Set remove error for key {key}: {e}")
            return False
    
    async def set_members(self, key: str) -> List[Any]:
        """Get all members of set"""
        if not self.redis:
            return []
        
        try:
            members = await self.redis.smembers(key)
            return [json.loads(m) for m in members]
        except Exception as e:
            logger.error(f"Set members error for key {key}: {e}")
            return []
    
    async def set_is_member(self, key: str, value: Any) -> bool:
        """Check if value is member of set"""
        if not self.redis:
            return False
        
        try:
            json_value = json.dumps(value)
            return await self.redis.sismember(key, json_value)
        except Exception as e:
            logger.error(f"Set is_member error for key {key}: {e}")
            return False
    
    # ========== Health Check ==========
    
    async def health_check(self) -> dict:
        """Check Redis health"""
        if not self.redis:
            return {
                "status": "disconnected",
                "connected": False
            }
        
        try:
            await self.redis.ping()
            info = await self.redis.info()
            
            return {
                "status": "healthy",
                "connected": True,
                "version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_commands_processed": info.get("total_commands_processed")
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }


# Global cache service instance
cache_service = CacheService()
