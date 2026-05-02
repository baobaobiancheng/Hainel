"""
API v1 路由模块
注册所有v1版本的API路由

路由注册采用惰性加载（lazy import），避免模块初始化时触发重量级依赖（langchain/torch 等）。
main.py 调用 setup_routes() 完整注册；main_dev.py 只按需注册部分路由。
"""
from fastapi import APIRouter

# 创建全局路由器（空，等待 setup_routes() 填充）
api_router = APIRouter()


def setup_routes() -> None:
    """注册全部 API 路由（供 main.py 调用）"""
    from app.api.v1 import (
        auth,
        conversations,
        messages,
        medical_records,
        reports,
        long_polling,
        reminders,
        knowledge,
        agents,
        doctors,
    )

    # 已有路由
    api_router.include_router(auth.router)
    api_router.include_router(conversations.router)
    api_router.include_router(messages.router)
    api_router.include_router(medical_records.router)
    api_router.include_router(reports.router)
    api_router.include_router(long_polling.router)

    # 新增路由
    api_router.include_router(reminders.router)
    api_router.include_router(knowledge.router)
    api_router.include_router(agents.router)
    api_router.include_router(doctors.router)


# 导出
__all__ = ["api_router", "setup_routes"]

