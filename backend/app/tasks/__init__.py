"""
异步任务模块
导出所有Celery任务
"""
from app.tasks.celery_app import celery_app

# 导入任务模块（确保任务被注册）
from app.tasks import reminder_tasks, training_tasks, notification_tasks

# 导出
__all__ = [
    "celery_app",
    "reminder_tasks",
    "training_tasks",
    "notification_tasks",
]

