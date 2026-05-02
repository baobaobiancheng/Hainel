"""
数据库会话管理
提供数据库会话的创建、管理和事务处理
"""
from contextlib import contextmanager
from typing import Generator, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.database.base import SessionLocal
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseSession:
    """数据库会话管理器"""
    
    def __init__(self, session: Optional[Session] = None):
        """
        初始化数据库会话管理器
        
        Args:
            session: 可选的会话对象，如果不提供则创建新会话
        """
        self._session = session or SessionLocal()
        self._is_managed = session is None
    
    def __enter__(self):
        """上下文管理器入口"""
        return self._session
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        if exc_type is not None:
            # 发生异常时回滚
            self.rollback()
            logger.error(f"数据库操作发生异常: {exc_type.__name__}: {exc_val}")
        else:
            # 正常情况提交
            self.commit()
        
        # 如果是我们创建的会话，则关闭它
        if self._is_managed:
            self.close()
    
    @property
    def session(self) -> Session:
        """获取会话对象"""
        return self._session
    
    def commit(self):
        """提交事务"""
        try:
            self._session.commit()
            logger.debug("数据库事务已提交")
        except SQLAlchemyError as e:
            self._session.rollback()
            logger.error(f"提交事务失败: {e}")
            raise
    
    def rollback(self):
        """回滚事务"""
        try:
            self._session.rollback()
            logger.debug("数据库事务已回滚")
        except SQLAlchemyError as e:
            logger.error(f"回滚事务失败: {e}")
            raise
    
    def close(self):
        """关闭会话"""
        try:
            self._session.close()
            logger.debug("数据库会话已关闭")
        except SQLAlchemyError as e:
            logger.error(f"关闭会话失败: {e}")
            raise
    
    def flush(self):
        """刷新会话（将更改发送到数据库但不提交）"""
        try:
            self._session.flush()
            logger.debug("数据库会话已刷新")
        except SQLAlchemyError as e:
            self._session.rollback()
            logger.error(f"刷新会话失败: {e}")
            raise


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """
    获取数据库会话的上下文管理器
    
    Yields:
        Session: 数据库会话对象
    
    Usage:
        with get_session() as session:
            user = User(name="test")
            session.add(user)
            # 自动提交或回滚
    """
    db_session = DatabaseSession()
    try:
        yield db_session.session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


@contextmanager
def transaction(session: Optional[Session] = None) -> Generator[Session, None, None]:
    """
    事务上下文管理器
    
    Args:
        session: 可选的会话对象，如果不提供则创建新会话
    
    Yields:
        Session: 数据库会话对象
    
    Usage:
        with transaction() as session:
            user = User(name="test")
            session.add(user)
            # 自动提交或回滚
    """
    db_session = DatabaseSession(session)
    try:
        yield db_session.session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        if session is None:
            db_session.close()


def get_db_session() -> Session:
    """
    获取新的数据库会话
    
    Returns:
        Session: 数据库会话对象
    
    Note:
        调用者负责关闭会话，建议使用上下文管理器
    """
    return SessionLocal()


# 导出
__all__ = [
    "DatabaseSession",
    "get_session",
    "transaction",
    "get_db_session",
]

