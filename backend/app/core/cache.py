"""
Redis 缓存管理
"""
import json
from typing import Any, Optional
from redis.asyncio import Redis
from loguru import logger
from app.config import settings


class RedisCache:
    """Redis 缓存管理器"""
    
    def __init__(self):
        self.redis: Optional[Redis] = None
    
    async def connect(self):
        """连接 Redis"""
        try:
            self.redis = Redis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                encoding="utf-8",
            )
            await self.redis.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            self.redis = None
    
    async def close(self):
        """关闭 Redis 连接"""
        if self.redis:
            await self.redis.close()
            logger.info("Redis connection closed")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.redis:
            return None
        
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600,
    ) -> bool:
        """设置缓存"""
        if not self.redis:
            return False
        
        try:
            await self.redis.setex(
                key,
                expire,
                json.dumps(value, ensure_ascii=False),
            )
            return True
        except Exception as e:
            logger.error(f"Redis set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.redis:
            return False
        
        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete error: {e}")
            return False
    
    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        if not self.redis:
            return False
        
        try:
            return await self.redis.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists error: {e}")
            return False


# 全局缓存实例
cache = RedisCache()

