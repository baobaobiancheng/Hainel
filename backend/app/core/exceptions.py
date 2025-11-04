"""
自定义异常类
"""
from typing import Optional, Any
from fastapi import status


class AppException(Exception):
    """应用基础异常类"""
    
    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "APP_ERROR",
        detail: Optional[Any] = None,
    ):
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.detail = detail
        super().__init__(self.message)


# ==================== 认证相关异常 ====================

class AuthenticationError(AppException):
    """认证失败异常"""
    
    def __init__(
        self,
        message: str = "认证失败",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="AUTHENTICATION_ERROR",
            detail=detail,
        )


class PermissionDenied(AppException):
    """权限不足异常"""
    
    def __init__(
        self,
        message: str = "权限不足",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="PERMISSION_DENIED",
            detail=detail,
        )


class TokenExpired(AppException):
    """Token 过期异常"""
    
    def __init__(
        self,
        message: str = "Token 已过期",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="TOKEN_EXPIRED",
            detail=detail,
        )


class InvalidToken(AppException):
    """无效 Token 异常"""
    
    def __init__(
        self,
        message: str = "无效的 Token",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_401_UNAUTHORIZED,
            error_code="INVALID_TOKEN",
            detail=detail,
        )


# ==================== 资源相关异常 ====================

class NotFound(AppException):
    """资源未找到异常"""
    
    def __init__(
        self,
        message: str = "资源未找到",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="NOT_FOUND",
            detail=detail,
        )


class AlreadyExists(AppException):
    """资源已存在异常"""
    
    def __init__(
        self,
        message: str = "资源已存在",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_409_CONFLICT,
            error_code="ALREADY_EXISTS",
            detail=detail,
        )


# ==================== 业务逻辑异常 ====================

class ValidationError(AppException):
    """数据验证失败异常"""
    
    def __init__(
        self,
        message: str = "数据验证失败",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            error_code="VALIDATION_ERROR",
            detail=detail,
        )


class BusinessLogicError(AppException):
    """业务逻辑错误异常"""
    
    def __init__(
        self,
        message: str = "业务逻辑错误",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_400_BAD_REQUEST,
            error_code="BUSINESS_LOGIC_ERROR",
            detail=detail,
        )


# ==================== 外部服务异常 ====================

class ExternalServiceError(AppException):
    """外部服务错误异常"""
    
    def __init__(
        self,
        message: str = "外部服务错误",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="EXTERNAL_SERVICE_ERROR",
            detail=detail,
        )


class AIServiceError(AppException):
    """AI 服务错误异常"""
    
    def __init__(
        self,
        message: str = "AI 服务错误",
        detail: Optional[Any] = None,
    ):
        super().__init__(
            message=message,
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            error_code="AI_SERVICE_ERROR",
            detail=detail,
        )

