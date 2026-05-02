"""
SQLAlchemy Base
定义数据库基础类和元数据
"""
from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Generator

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)

# 创建数据库引擎
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # 连接前ping，检测连接是否有效
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接数
    pool_recycle=3600,  # 连接回收时间（秒）
    echo=settings.DEBUG,  # 是否打印SQL语句
    future=True,  # 使用SQLAlchemy 2.0风格
)

# 创建会话工厂
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    future=True,
)

# 定义元数据
metadata = MetaData()

# 创建基础模型类
Base = declarative_base(metadata=metadata)


def get_db() -> Generator:
    """
    获取数据库会话（依赖注入）
    
    Yields:
        Session: 数据库会话对象
    
    Usage:
        @app.get("/api/users")
        async def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库（创建所有表）
    
    Note:
        也可以直接使用 init_database.sql 文件来初始化数据库
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("数据库表创建成功")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}")
        raise


def drop_db():
    """
    删除所有数据库表（谨慎使用）
    
    Warning:
        此操作会删除所有数据，仅用于开发环境
    """
    try:
        Base.metadata.drop_all(bind=engine)
        logger.warning("数据库表已删除")
    except Exception as e:
        logger.error(f"删除数据库表失败: {e}")
        raise


# 导出
__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "metadata",
    "get_db",
    "init_db",
    "drop_db",
]

