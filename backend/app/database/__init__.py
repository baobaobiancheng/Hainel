"""
数据库访问层
提供数据库连接、会话管理和Redis客户端
"""
from app.database.base import (
    Base,
    engine,
    SessionLocal,
    metadata,
    get_db,
    init_db,
    drop_db,
)
from app.database.session import (
    DatabaseSession,
    get_session,
    transaction,
    get_db_session,
)
from app.database.redis_client import (
    RedisClient,
    redis_client,
)

# 导出
__all__ = [
    # Base和引擎
    "Base",
    "engine",
    "SessionLocal",
    "metadata",
    "get_db",
    "init_db",
    "drop_db",
    # 会话管理
    "DatabaseSession",
    "get_session",
    "transaction",
    "get_db_session",
    # Redis客户端
    "RedisClient",
    "redis_client",
]

