"""
中间件模块
提供日志、CORS、请求ID等中间件
"""
import time
import uuid
from typing import Callable
from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件，为每个请求添加唯一ID"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # WebSocket 连接直接放行，不处理
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # 生成请求ID
        request_id = str(uuid.uuid4())
        
        # 将请求ID添加到请求状态
        request.state.request_id = request_id
        
        # 调用下一个中间件或路由处理函数
        response = await call_next(request)
        
        # 将请求ID添加到响应头
        response.headers["X-Request-ID"] = request_id
        
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """日志中间件，记录请求和响应信息"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # WebSocket 连接直接放行
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        # 记录请求开始时间
        start_time = time.time()
        
        # 获取请求ID
        request_id = getattr(request.state, "request_id", "unknown")
        
        # 记录请求信息
        logger.info(
            f"请求开始 - ID: {request_id}, "
            f"方法: {request.method}, "
            f"路径: {request.url.path}, "
            f"客户端: {request.client.host if request.client else 'unknown'}"
        )
        
        try:
            # 调用下一个中间件或路由处理函数
            response = await call_next(request)
            
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录响应信息
            logger.info(
                f"请求完成 - ID: {request_id}, "
                f"状态码: {response.status_code}, "
                f"处理时间: {process_time:.3f}秒"
            )
            
            # 添加处理时间到响应头
            response.headers["X-Process-Time"] = str(process_time)
            
            return response
        except Exception as e:
            # 计算处理时间
            process_time = time.time() - start_time
            
            # 记录错误信息
            logger.error(
                f"请求失败 - ID: {request_id}, "
                f"错误: {str(e)}, "
                f"处理时间: {process_time:.3f}秒",
                exc_info=True
            )
            raise


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """安全头中间件，添加安全相关的HTTP头"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # WebSocket 连接直接放行
        if request.scope.get("type") == "websocket":
            return await call_next(request)

        response = await call_next(request)
        
        # 添加安全头
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        
        return response


def setup_cors_middleware(app: ASGIApp) -> None:
    """
    设置CORS中间件
    
    Args:
        app: FastAPI应用实例
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )


def setup_middlewares(app: ASGIApp) -> None:
    """
    设置所有中间件
    
    Args:
        app: FastAPI应用实例
    """
    # 添加请求ID中间件（最先添加，确保其他中间件可以使用request_id）
    app.add_middleware(RequestIDMiddleware)
    
    # 添加日志中间件
    app.add_middleware(LoggingMiddleware)
    
    # 添加安全头中间件
    app.add_middleware(SecurityHeadersMiddleware)
    
    # 设置CORS中间件
    setup_cors_middleware(app)
    
    logger.info("中间件设置完成")


# 导出
__all__ = [
    "RequestIDMiddleware",
    "LoggingMiddleware",
    "SecurityHeadersMiddleware",
    "setup_cors_middleware",
    "setup_middlewares",
]

