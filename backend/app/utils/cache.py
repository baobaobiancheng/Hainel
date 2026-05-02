"""
缓存工具模块
提供Redis缓存操作功能
"""
import json
import pickle
from typing import Any, Optional
from functools import wraps
import redis
from redis.exceptions import RedisError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CacheError(Exception):
    """缓存操作异常"""
    pass


class RedisCache:
    """Redis缓存客户端封装"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: Optional[int] = None,
        decode_responses: Optional[bool] = None,
    ):
        """
        初始化Redis客户端
        
        Args:
            host: Redis主机地址
            port: Redis端口
            password: Redis密码
            db: Redis数据库编号
            decode_responses: 是否自动解码响应
        """
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.password = password or settings.REDIS_PASSWORD
        self.db = db or settings.REDIS_DB
        self.decode_responses = decode_responses or settings.REDIS_DECODE_RESPONSES
        self.prefix = settings.CACHE_PREFIX
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """获取Redis客户端实例（懒加载）"""
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    decode_responses=self.decode_responses,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                )
                # 测试连接
                self._client.ping()
                logger.info(f"Redis连接成功: {self.host}:{self.port}/{self.db}")
            except RedisError as e:
                logger.error(f"Redis连接失败: {e}")
                raise CacheError(f"Redis连接失败: {e}")
        return self._client
    
    def _make_key(self, key: str) -> str:
        """生成带前缀的缓存键"""
        return f"{self.prefix}{key}"
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
        
        Returns:
            缓存值，如果不存在返回default
        """
        try:
            full_key = self._make_key(key)
            value = self.client.get(full_key)
            if value is None:
                return default
            
            # 尝试JSON解析
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，尝试pickle解析
                try:
                    return pickle.loads(value)
                except (pickle.PickleError, TypeError):
                    # 如果都失败，直接返回原始值
                    return value
        except RedisError as e:
            logger.error(f"获取缓存失败: {key}, 错误: {e}")
            return default
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        serialize: bool = True,
    ) -> bool:
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None表示使用默认TTL
            serialize: 是否序列化（JSON或pickle）
        
        Returns:
            是否设置成功
        """
        try:
            full_key = self._make_key(key)
            ttl = ttl if ttl is not None else settings.CACHE_DEFAULT_TTL
            
            # 序列化值
            if serialize:
                try:
                    # 优先使用JSON（支持基本类型）
                    serialized_value = json.dumps(value, ensure_ascii=False)
                except (TypeError, ValueError):
                    # JSON失败则使用pickle
                    serialized_value = pickle.dumps(value)
            else:
                serialized_value = value
            
            return self.client.setex(full_key, ttl, serialized_value)
        except RedisError as e:
            logger.error(f"设置缓存失败: {key}, 错误: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        删除缓存
        
        Args:
            key: 缓存键
        
        Returns:
            是否删除成功
        """
        try:
            full_key = self._make_key(key)
            return bool(self.client.delete(full_key))
        except RedisError as e:
            logger.error(f"删除缓存失败: {key}, 错误: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在
        
        Args:
            key: 缓存键
        
        Returns:
            是否存在
        """
        try:
            full_key = self._make_key(key)
            return bool(self.client.exists(full_key))
        except RedisError as e:
            logger.error(f"检查缓存失败: {key}, 错误: {e}")
            return False
    
    def expire(self, key: str, ttl: int) -> bool:
        """
        设置缓存过期时间
        
        Args:
            key: 缓存键
            ttl: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        try:
            full_key = self._make_key(key)
            return self.client.expire(full_key, ttl)
        except RedisError as e:
            logger.error(f"设置过期时间失败: {key}, 错误: {e}")
            return False
    
    def clear_pattern(self, pattern: str) -> int:
        """
        清除匹配模式的所有缓存
        
        Args:
            pattern: 匹配模式（支持通配符）
        
        Returns:
            删除的缓存数量
        """
        try:
            full_pattern = self._make_key(pattern)
            keys = self.client.keys(full_pattern)
            if keys:
                return self.client.delete(*keys)
            return 0
        except RedisError as e:
            logger.error(f"清除缓存失败: {pattern}, 错误: {e}")
            return 0
    
    def clear_all(self) -> bool:
        """
        清除所有缓存（谨慎使用）
        
        Returns:
            是否清除成功
        """
        try:
            pattern = f"{self.prefix}*"
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
            return True
        except RedisError as e:
            logger.error(f"清除所有缓存失败: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        获取缓存剩余过期时间
        
        Args:
            key: 缓存键
        
        Returns:
            剩余秒数，-1表示永不过期，-2表示不存在
        """
        try:
            full_key = self._make_key(key)
            return self.client.ttl(full_key)
        except RedisError as e:
            logger.error(f"获取TTL失败: {key}, 错误: {e}")
            return -2


# 创建全局缓存实例
cache = RedisCache()


def cached(key_prefix: str, ttl: Optional[int] = None):
    """
    缓存装饰器
    
    Args:
        key_prefix: 缓存键前缀
        ttl: 过期时间（秒），None表示使用默认TTL
    
    Usage:
        @cached("user", ttl=3600)
        def get_user(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{args}:{kwargs}"
            
            # 尝试从缓存获取
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行函数
            result = func(*args, **kwargs)
            
            # 存入缓存
            cache.set(cache_key, result, ttl=ttl)
            
            return result
        return wrapper
    return decorator


# 导出
__all__ = ["cache", "RedisCache", "CacheError", "cached"]

