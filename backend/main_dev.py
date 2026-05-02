"""
开发入口 —— 启动首页 + 登录 + 仪表盘/患者管理所需路由
运行方式：uv run uvicorn main_dev:app --reload --port 8001
"""
import os
# 强制使用离线模式，避免联网下载模型
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import settings
from app.core.exceptions import BaseAppException, to_http_exception
from app.core.middleware import setup_middlewares
from app.utils.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("=" * 50)
    logger.info(f"[DEV] 启动开发模式 — 首页 + 登录 + 核心业务路由")
    logger.info(f"项目: {settings.PROJECT_NAME} v{settings.PROJECT_VERSION}")
    logger.info("=" * 50)

    # 尝试数据库连接，失败只警告不退出
    try:
        from sqlalchemy import text
        from app.database.session import get_db_session
        db = get_db_session()
        db.execute(text("SELECT 1"))
        db.close()
        logger.info("数据库连接: OK")
    except Exception as e:
        logger.warning(f"数据库连接失败 (不影响启动): {e}")

    yield

    logger.info("[DEV] 应用关闭")


app = FastAPI(
    title=f"{settings.PROJECT_NAME} [DEV]",
    version=settings.PROJECT_VERSION,
    description="开发模式 — 首页 + 登录 + 核心业务路由",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

setup_middlewares(app)

# 在 app 创建后再 import，避免触发 __init__.py 里的重量级依赖（langchain/torch 等）
from app.api.v1.auth import router as auth_router              # noqa: E402
from app.api.v1.conversations import router as conv_router     # noqa: E402
from app.api.v1.medical_records import router as records_router  # noqa: E402
from app.api.v1.messages import router as messages_router      # noqa: E402
from app.api.v1.doctors import router as doctors_router        # noqa: E402
from app.api.v1.knowledge import router as knowledge_router    # noqa: E402
from app.api.v1.agents import router as agents_router          # noqa: E402
from app.api.v1.reminders import router as reminders_router    # noqa: E402
from app.api.v1.long_polling import router as poll_router      # noqa: E402
from app.api.v1.websocket import router as websocket_router      # noqa: E402
from app.api.v1.consultation import router as consultation_router  # noqa: E402
from app.api.v1.reports import router as reports_router            # noqa: E402

app.include_router(auth_router,     prefix=settings.API_V1_PREFIX)
app.include_router(conv_router,     prefix=settings.API_V1_PREFIX)
app.include_router(records_router,  prefix=settings.API_V1_PREFIX)
app.include_router(messages_router, prefix=settings.API_V1_PREFIX)
app.include_router(doctors_router,  prefix=settings.API_V1_PREFIX)
app.include_router(knowledge_router, prefix=settings.API_V1_PREFIX)
app.include_router(agents_router, prefix=settings.API_V1_PREFIX)
app.include_router(reminders_router, prefix=settings.API_V1_PREFIX)
app.include_router(poll_router,     prefix=settings.API_V1_PREFIX)
app.include_router(consultation_router, prefix=settings.API_V1_PREFIX)
app.include_router(reports_router, prefix=settings.API_V1_PREFIX)

# 注册WebSocket路由（使用/ws前缀）
app.include_router(websocket_router, prefix="/ws", tags=["WebSocket"])

# 静态文件服务（用于 OCR 图片识别）
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


# ---------- 异常处理 ----------

@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    http_exc = to_http_exception(exc)
    return JSONResponse(status_code=http_exc.status_code, content=http_exc.detail)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTPException", "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "ValidationError", "message": "请求数据验证失败", "details": exc.errors()},
    )


# ---------- 首页 ----------

@app.get("/", tags=["系统"])
async def root():
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.PROJECT_VERSION,
        "mode": "dev-minimal",
        "status": "running",
        "docs": "/docs",
        "active_routes": [
            "POST /api/v1/auth/register",
            "POST /api/v1/auth/login",
            "POST /api/v1/auth/logout",
            "GET  /api/v1/auth/me",
            "PUT  /api/v1/auth/me",
            "POST /api/v1/auth/change-password",
            "GET  /api/v1/conversations",
            "POST /api/v1/conversations",
            "GET  /api/v1/conversations/{id}",
            "PATCH /api/v1/conversations/{id}/status",
            "GET  /api/v1/medical-records",
            "GET  /api/v1/medical-records/{id}",
            "POST /api/v1/medical-records/{id}/review",
            "GET  /api/v1/messages/conversation/{id}",
            "GET  /api/v1/doctors/patients",
            "GET  /api/v1/doctors/conversations",
            "GET  /api/v1/doctors/patients/{id}/summary",
            "GET  /api/v1/knowledge/search",
            "GET  /api/v1/knowledge/{id}",
            "GET  /api/v1/reminders/",
            "POST /api/v1/reminders/",
            "PUT  /api/v1/reminders/{id}",
            "DELETE /api/v1/reminders/{id}",
        ],
    }


@app.get("/health", tags=["系统"])
async def health():
    return {"status": "ok", "mode": "dev-minimal"}
