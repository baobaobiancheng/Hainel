"""
依赖注入模块
提供FastAPI依赖注入函数，用于获取数据库会话、当前用户等
"""
from typing import Generator, Optional
from fastapi import Header
from sqlalchemy.orm import Session

from app.database.session import get_db_session
from app.core.permissions import get_token_from_header
from app.core.security import security


# ========== 数据库依赖 ==========

def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话依赖
    
    用于FastAPI路由函数的依赖注入
    
    Yields:
        Session: 数据库会话对象
    """
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


# ========== 认证依赖 ==========

def get_current_user_optional(
    authorization: Optional[str] = Header(None)
) -> Optional[dict]:
    """
    获取当前用户（可选）
    
    如果请求头中没有 token，返回 None 而不是抛出异常，
    适用于可选认证的端点。
    """
    if not authorization:
        return None
    
    try:
        token = get_token_from_header(authorization)
        payload = security.decode_token(token)
        user_id = payload.get("sub") or payload.get("user_id")
        
        if not user_id:
            return None
        
        return {
            "id": int(user_id) if isinstance(user_id, str) else user_id,
            "role": payload.get("role", "patient"),
            "username": payload.get("username", ""),
        }
    except Exception:
        return None


# ========== 导出 ==========

__all__ = [
    "get_db",
    "get_current_user_optional",
]

