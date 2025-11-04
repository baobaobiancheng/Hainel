"""
FastAPI 应用主入口
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import time

from app.config import settings
from app.core.database import engine, Base
from app.core.exceptions import AppException
from app.api.v1 import auth, errors, ai, knowledge, practice, reports


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 Starting Smart Error Book API...")
    logger.info(f"Environment: {settings.APP_ENV}")
    logger.info(f"Debug Mode: {settings.DEBUG}")
    
    # 初始化数据库表（生产环境使用 Alembic）
    if settings.is_development:
        async with engine.begin() as conn:
            # await conn.run_sync(Base.metadata.drop_all)  # 谨慎使用
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database tables created")
    
    yield
    
    # 关闭时执行
    logger.info("🛑 Shutting down Smart Error Book API...")
    await engine.dispose()


# 创建 FastAPI 应用实例
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="智能错题本 - 后端 API 服务",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    lifespan=lifespan,
)


# ==================== 中间件配置 ====================

# CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Gzip 压缩
app.add_middleware(GZipMiddleware, minimum_size=1000)


# 请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    start_time = time.time()
    
    # 记录请求
    logger.info(f"➡️  {request.method} {request.url.path}")
    
    # 处理请求
    response = await call_next(request)
    
    # 计算耗时
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    
    # 记录响应
    logger.info(
        f"⬅️  {request.method} {request.url.path} "
        f"- Status: {response.status_code} - Time: {process_time:.3f}s"
    )
    
    return response


# ==================== 异常处理 ====================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """处理自定义应用异常"""
    logger.error(f"App Exception: {exc.message} - Detail: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.error_code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """处理请求验证异常"""
    logger.error(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "请求参数验证失败",
                "detail": exc.errors(),
            }
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """处理未捕获的异常"""
    logger.exception(f"Unhandled Exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "服务器内部错误",
                "detail": str(exc) if settings.DEBUG else None,
            }
        },
    )


# ==================== 路由注册 ====================

# 健康检查
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
    }


# API 根路径
@app.get("/", tags=["Root"])
async def root():
    """API 根路径"""
    return {
        "message": f"Welcome to {settings.APP_NAME} API",
        "version": settings.APP_VERSION,
        "docs": "/docs" if settings.DEBUG else "disabled",
    }


# 注册 v1 API 路由
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"],
)

app.include_router(
    errors.router,
    prefix=f"{settings.API_V1_PREFIX}/errors",
    tags=["Error Questions"],
)

app.include_router(
    ai.router,
    prefix=f"{settings.API_V1_PREFIX}/ai",
    tags=["AI Analysis"],
)

app.include_router(
    knowledge.router,
    prefix=f"{settings.API_V1_PREFIX}/knowledge",
    tags=["Knowledge Graph"],
)

app.include_router(
    practice.router,
    prefix=f"{settings.API_V1_PREFIX}/practice",
    tags=["Practice"],
)

app.include_router(
    reports.router,
    prefix=f"{settings.API_V1_PREFIX}/reports",
    tags=["Reports"],
)


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )

