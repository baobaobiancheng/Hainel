"""
FastAPI应用入口
配置应用、注册路由、设置中间件等
"""
import sys
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.middleware import setup_middlewares
from app.core.exceptions import (
    BaseAppException,
    to_http_exception,
)
from app.database.base import Base
from app.database.session import get_db_session
from app.api.v1 import api_router, setup_routes
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    应用生命周期管理
    在应用启动和关闭时执行相关操作
    """
    # 启动时执行
    logger.info("=" * 60)
    logger.info(f"启动 {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    logger.info(f"调试模式: {settings.DEBUG}")
    logger.info(f"数据库: {settings.MYSQL_HOST}:{settings.MYSQL_PORT}/{settings.MYSQL_DATABASE}")
    logger.info("=" * 60)
    
    # 测试数据库连接
    try:
        from sqlalchemy import text
        db = get_db_session()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        logger.info("数据库连接成功")
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        if not settings.DEBUG:
            logger.error("应用启动失败，退出")
            sys.exit(1)
    
    yield
    
    # 关闭时执行
    logger.info("应用正在关闭...")


# 创建FastAPI应用实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.PROJECT_VERSION,
    description="基于多智能体协同的医疗健康咨询与辅助诊断系统",
    debug=settings.DEBUG,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # 生产环境禁用文档
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)


# 注册路由（惰性加载，在此处触发全部模块的真实导入）
setup_routes()
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 注册WebSocket路由（使用/ws前缀）
from app.api.v1.websocket import router as websocket_router
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])


# 设置中间件
setup_middlewares(app)


# ========== 异常处理 ==========

@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    """
    处理应用自定义异常
    """
    logger.error(
        f"应用异常 - 路径: {request.url.path}, "
        f"错误: {exc.__class__.__name__}, "
        f"消息: {exc.message}"
    )
    
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content=http_exc.detail,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """
    处理HTTP异常
    """
    logger.warning(
        f"HTTP异常 - 路径: {request.url.path}, "
        f"状态码: {exc.status_code}, "
        f"详情: {exc.detail}"
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": "HTTPException",
            "message": str(exc.detail),
            "status_code": exc.status_code,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """
    处理请求验证异常
    """
    logger.warning(
        f"请求验证失败 - 路径: {request.url.path}, "
        f"错误: {exc.errors()}"
    )
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "ValidationError",
            "message": "请求数据验证失败",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    处理未捕获的异常
    """
    logger.error(
        f"未捕获的异常 - 路径: {request.url.path}, "
        f"错误类型: {exc.__class__.__name__}, "
        f"错误信息: {str(exc)}",
        exc_info=True
    )
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "InternalServerError",
            "message": "服务器内部错误" if not settings.DEBUG else str(exc),
            "details": {"type": exc.__class__.__name__} if settings.DEBUG else {},
        },
    )


# ========== 健康检查端点 ==========

@app.get("/", tags=["系统"])
async def root():
    """
    根路径，返回API信息
    """
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "status": "running",
        "docs_url": "/docs" if settings.DEBUG else None,
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """
    健康检查端点
    用于监控系统状态
    """
    # 检查数据库连接
    from sqlalchemy import text
    db_status = "ok"
    try:
        db = get_db_session()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.error(f"健康检查 - 数据库连接失败: {e}")
    
    return {
        "status": "healthy" if db_status == "ok" else "unhealthy",
        "database": db_status,
        "version": settings.PROJECT_VERSION,
    }


@app.get("/ready", tags=["系统"])
async def readiness_check():
    """
    就绪检查端点
    用于Kubernetes等容器编排系统的就绪探针
    """
    # 检查关键服务是否就绪
    checks = {
        "database": False,
    }
    
    from sqlalchemy import text
    try:
        db = get_db_session()
        try:
            db.execute(text("SELECT 1"))
        finally:
            db.close()
        checks["database"] = True
    except Exception as e:
        logger.error(f"就绪检查 - 数据库连接失败: {e}")
    
    all_ready = all(checks.values())
    
    status_code = status.HTTP_200_OK if all_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
        },
    )


@app.get("/live", tags=["系统"])
async def liveness_check():
    """
    存活检查端点
    用于Kubernetes等容器编排系统的存活探针
    """
    return {
        "status": "alive",
    }


# ========== 启动脚本 ==========

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

