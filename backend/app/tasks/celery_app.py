"""
Celery应用配置
配置Celery应用实例，用于异步任务处理
"""
from celery import Celery
from celery.schedules import crontab

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


# 创建Celery应用实例
celery_app = Celery(
    "medical_system",
    broker=settings.CELERY_BROKER_URL_AUTO,
    backend=settings.CELERY_RESULT_BACKEND_AUTO,
    include=[
        "app.tasks.reminder_tasks",
        "app.tasks.training_tasks",
        "app.tasks.notification_tasks",
    ],
)


# Celery配置
celery_app.conf.update(
    # 任务序列化配置
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    
    # 任务路由配置
    task_routes={
        "app.tasks.reminder_tasks.*": {"queue": "reminders"},
        "app.tasks.training_tasks.*": {"queue": "training"},
        "app.tasks.notification_tasks.*": {"queue": "notifications"},
    },
    
    # 任务执行配置
    task_acks_late=True,  # 任务完成后才确认
    task_reject_on_worker_lost=True,  # worker丢失时拒绝任务
    task_time_limit=300,  # 任务硬超时（秒）
    task_soft_time_limit=240,  # 任务软超时（秒）
    
    # Worker配置
    worker_prefetch_multiplier=1,  # 每个worker预取任务数
    worker_max_tasks_per_child=1000,  # 每个worker子进程最大任务数
    
    # 结果后端配置
    result_expires=3600,  # 结果过期时间（秒）
    result_backend_transport_options={
        "master_name": "mymaster",
        "visibility_timeout": 3600,
    },
    
    # 定时任务配置
    beat_schedule={
        # 检查并发送用药提醒
        "check-reminders": {
            "task": "app.tasks.reminder_tasks.check_and_send_reminders",
            "schedule": crontab(minute="*/15"),  # 每15分钟执行一次
        },
        
        # 清理过期会话
        "cleanup-expired-conversations": {
            "task": "app.tasks.notification_tasks.cleanup_expired_conversations",
            "schedule": crontab(hour=2, minute=0),  # 每天凌晨2点执行
        },
        
        # 归档旧病历
        "archive-old-records": {
            "task": "app.tasks.notification_tasks.archive_old_medical_records",
            "schedule": crontab(hour=3, minute=0),  # 每天凌晨3点执行
        },
        
        # 训练智能体（可选，根据需求调整）
        # "train-agents": {
        #     "task": "app.tasks.training_tasks.train_agents_batch",
        #     "schedule": crontab(hour=4, minute=0),  # 每天凌晨4点执行
        # },
    },
)


# 任务基类配置
@celery_app.task(bind=True)
def debug_task(self):
    """
    调试任务，用于测试Celery配置
    """
    logger.info(f"调试任务执行: {self.request!r}")


# 导出
__all__ = ["celery_app"]

