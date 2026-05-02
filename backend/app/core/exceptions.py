"""
自定义异常模块
定义应用中的自定义异常类
"""
from typing import Optional, Dict, Any
from fastapi import HTTPException, status

from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str = "应用错误",
        code: int = 500,
        details: Optional[Dict[str, Any]] = None,
    ):
        """
        初始化异常
        
        Args:
            message: 错误消息
            code: 错误代码
            details: 错误详情
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code,
            "details": self.details,
        }


class ValidationException(BaseAppException):
    """验证异常"""
    
    def __init__(self, message: str = "数据验证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=400, details=details)


class AuthenticationException(BaseAppException):
    """认证异常"""
    
    def __init__(self, message: str = "认证失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=401, details=details)


class AuthorizationException(BaseAppException):
    """授权异常"""
    
    def __init__(self, message: str = "权限不足", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=403, details=details)


class NotFoundException(BaseAppException):
    """资源未找到异常"""
    
    def __init__(self, message: str = "资源未找到", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=404, details=details)


class ConflictException(BaseAppException):
    """冲突异常（如资源已存在）"""
    
    def __init__(self, message: str = "资源冲突", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=409, details=details)


class BusinessException(BaseAppException):
    """业务逻辑异常"""
    
    def __init__(self, message: str = "业务逻辑错误", code: int = 400, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=code, details=details)


class DatabaseException(BaseAppException):
    """数据库异常"""
    
    def __init__(self, message: str = "数据库操作失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=500, details=details)


class ExternalServiceException(BaseAppException):
    """外部服务异常"""
    
    def __init__(self, message: str = "外部服务调用失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=502, details=details)


class AIServiceException(BaseAppException):
    """AI服务异常"""
    
    def __init__(self, message: str = "AI服务调用失败", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=503, details=details)


class RateLimitException(BaseAppException):
    """限流异常"""
    
    def __init__(self, message: str = "请求过于频繁", details: Optional[Dict[str, Any]] = None):
        super().__init__(message, code=429, details=details)


# FastAPI HTTP异常映射
def to_http_exception(exc: BaseAppException) -> HTTPException:
    """
    将自定义异常转换为FastAPI HTTPException
    
    Args:
        exc: 自定义异常
    
    Returns:
        HTTPException
    """
    status_code_map = {
        400: status.HTTP_400_BAD_REQUEST,
        401: status.HTTP_401_UNAUTHORIZED,
        403: status.HTTP_403_FORBIDDEN,
        404: status.HTTP_404_NOT_FOUND,
        409: status.HTTP_409_CONFLICT,
        429: status.HTTP_429_TOO_MANY_REQUESTS,
        500: status.HTTP_500_INTERNAL_SERVER_ERROR,
        502: status.HTTP_502_BAD_GATEWAY,
        503: status.HTTP_503_SERVICE_UNAVAILABLE,
    }
    
    status_code = status_code_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
        }
    )


# 导出
__all__ = [
    "BaseAppException",
    "ValidationException",
    "AuthenticationException",
    "AuthorizationException",
    "NotFoundException",
    "ConflictException",
    "BusinessException",
    "DatabaseException",
    "ExternalServiceException",
    "AIServiceException",
    "RateLimitException",
    "to_http_exception",
]

