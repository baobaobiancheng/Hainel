"""
Redis客户端
提供基础的Redis连接和操作功能
"""
import redis
from typing import Optional, Any
from redis.exceptions import RedisError, ConnectionError, TimeoutError

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RedisClient:
    """Redis客户端封装类"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        password: Optional[str] = None,
        db: Optional[int] = None,
        decode_responses: Optional[bool] = None,
        socket_connect_timeout: int = 5,
        socket_timeout: int = 5,
    ):
        """
        初始化Redis客户端
        
        Args:
            host: Redis主机地址
            port: Redis端口
            password: Redis密码
            db: Redis数据库编号
            decode_responses: 是否自动解码响应
            socket_connect_timeout: 连接超时时间（秒）
            socket_timeout: 套接字超时时间（秒）
        """
        self.host = host or settings.REDIS_HOST
        self.port = port or settings.REDIS_PORT
        self.password = password or settings.REDIS_PASSWORD
        self.db = db or settings.REDIS_DB
        self.decode_responses = decode_responses or settings.REDIS_DECODE_RESPONSES
        self.socket_connect_timeout = socket_connect_timeout
        self.socket_timeout = socket_timeout
        
        self._client: Optional[redis.Redis] = None
    
    @property
    def client(self) -> redis.Redis:
        """
        获取Redis客户端实例（懒加载）
        
        Returns:
            redis.Redis: Redis客户端实例
        
        Raises:
            RedisError: Redis连接失败
        """
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=self.host,
                    port=self.port,
                    password=self.password,
                    db=self.db,
                    decode_responses=self.decode_responses,
                    socket_connect_timeout=self.socket_connect_timeout,
                    socket_timeout=self.socket_timeout,
                )
                # 测试连接
                self._client.ping()
                logger.info(f"Redis连接成功: {self.host}:{self.port}/{self.db}")
            except (ConnectionError, TimeoutError) as e:
                logger.error(f"Redis连接失败: {e}")
                raise RedisError(f"Redis连接失败: {e}")
            except RedisError as e:
                logger.error(f"Redis操作失败: {e}")
                raise
        
        return self._client
    
    def ping(self) -> bool:
        """
        测试Redis连接
        
        Returns:
            bool: 连接是否正常
        """
        try:
            return self.client.ping()
        except RedisError as e:
            logger.error(f"Redis ping失败: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """
        获取键值
        
        Args:
            key: 键名
        
        Returns:
            键值，如果不存在返回None
        """
        try:
            return self.client.get(key)
        except RedisError as e:
            logger.error(f"Redis GET失败: {key}, 错误: {e}")
            return None
    
    def set(
        self,
        key: str,
        value: Any,
        ex: Optional[int] = None,
        px: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        设置键值
        
        Args:
            key: 键名
            value: 值
            ex: 过期时间（秒）
            px: 过期时间（毫秒）
            nx: 仅在键不存在时设置
            xx: 仅在键存在时设置
        
        Returns:
            是否设置成功
        """
        try:
            return bool(
                self.client.set(
                    key,
                    value,
                    ex=ex,
                    px=px,
                    nx=nx,
                    xx=xx,
                )
            )
        except RedisError as e:
            logger.error(f"Redis SET失败: {key}, 错误: {e}")
            return False
    
    def delete(self, *keys: str) -> int:
        """
        删除键
        
        Args:
            *keys: 要删除的键名
        
        Returns:
            删除的键数量
        """
        try:
            return self.client.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DELETE失败: {keys}, 错误: {e}")
            return 0
    
    def exists(self, *keys: str) -> int:
        """
        检查键是否存在
        
        Args:
            *keys: 要检查的键名
        
        Returns:
            存在的键数量
        """
        try:
            return self.client.exists(*keys)
        except RedisError as e:
            logger.error(f"Redis EXISTS失败: {keys}, 错误: {e}")
            return 0
    
    def expire(self, key: str, time: int) -> bool:
        """
        设置键的过期时间
        
        Args:
            key: 键名
            time: 过期时间（秒）
        
        Returns:
            是否设置成功
        """
        try:
            return self.client.expire(key, time)
        except RedisError as e:
            logger.error(f"Redis EXPIRE失败: {key}, 错误: {e}")
            return False
    
    def ttl(self, key: str) -> int:
        """
        获取键的剩余过期时间
        
        Args:
            key: 键名
        
        Returns:
            剩余秒数，-1表示永不过期，-2表示不存在
        """
        try:
            return self.client.ttl(key)
        except RedisError as e:
            logger.error(f"Redis TTL失败: {key}, 错误: {e}")
            return -2
    
    def keys(self, pattern: str = "*") -> list:
        """
        获取匹配模式的所有键
        
        Args:
            pattern: 匹配模式（支持通配符）
        
        Returns:
            键列表
        """
        try:
            return self.client.keys(pattern)
        except RedisError as e:
            logger.error(f"Redis KEYS失败: {pattern}, 错误: {e}")
            return []
    
    def close(self):
        """关闭Redis连接"""
        if self._client is not None:
            try:
                self._client.close()
                self._client = None
                logger.info("Redis连接已关闭")
            except RedisError as e:
                logger.error(f"关闭Redis连接失败: {e}")
    
    def __del__(self):
        """析构函数，确保连接被关闭"""
        self.close()


# 创建全局Redis客户端实例
redis_client = RedisClient()


# 导出
__all__ = [
    "RedisClient",
    "redis_client",
]

