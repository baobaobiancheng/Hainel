"""
提醒任务模块
处理用药提醒相关的异步任务
"""
from datetime import datetime
from celery import Task
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.database.session import get_db_session
from app.utils.logger import get_logger

logger = get_logger(__name__)


class DatabaseTask(Task):
    """
    数据库任务基类
    自动管理数据库会话
    """
    
    def __call__(self, *args, **kwargs):
        """
        执行任务，自动管理数据库会话
        """
        with get_db_session() as db:
            return self.run(db, *args, **kwargs)
    
    def run(self, db: Session, *args, **kwargs):
        """
        子类需要实现此方法
        """
        raise NotImplementedError("子类必须实现run方法")


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.reminder_tasks.check_and_send_reminders",
    max_retries=3,
    default_retry_delay=60,
)
def check_and_send_reminders(self, db: Session):
    """
    检查并发送用药提醒
    
    定期检查需要发送的用药提醒，并发送通知
    
    Args:
        db: 数据库会话
    """
    try:
        logger.info("开始检查用药提醒")
        
        # TODO: 实现提醒检查逻辑
        # 1. 查询即将到期的提醒（例如：15分钟内需要提醒的）
        # 2. 发送提醒通知（通过WebSocket或推送服务）
        # 3. 更新提醒状态
        
        # 示例代码结构：
        # reminders = ReminderService.get_pending_reminders(db, minutes_ahead=15)
        # for reminder in reminders:
        #     send_reminder_notification(reminder)
        #     ReminderService.mark_reminder_sent(reminder.id, db)
        
        logger.info("用药提醒检查完成")
        return {"status": "success", "checked_at": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error(f"检查用药提醒失败: {e}", exc_info=True)
        # 重试任务
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.reminder_tasks.send_reminder",
    max_retries=3,
    default_retry_delay=30,
)
def send_reminder(self, db: Session, reminder_id: int, user_id: int):
    """
    发送单个用药提醒
    
    Args:
        db: 数据库会话
        reminder_id: 提醒ID
        user_id: 用户ID
    """
    try:
        logger.info(f"发送用药提醒 - 提醒ID: {reminder_id}, 用户ID: {user_id}")
        
        # TODO: 实现提醒发送逻辑
        # 1. 查询提醒信息
        # 2. 构建提醒消息
        # 3. 通过WebSocket或推送服务发送
        # 4. 记录发送日志
        
        # 示例代码结构：
        # reminder = ReminderService.get_reminder_by_id(reminder_id, db)
        # if reminder and reminder.user_id == user_id:
        #     message = build_reminder_message(reminder)
        #     send_notification(user_id, message)
        #     ReminderService.mark_reminder_sent(reminder_id, db)
        
        logger.info(f"用药提醒发送成功 - 提醒ID: {reminder_id}")
        return {"status": "success", "reminder_id": reminder_id}
        
    except Exception as e:
        logger.error(f"发送用药提醒失败 - 提醒ID: {reminder_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.reminder_tasks.create_recurring_reminders",
    max_retries=3,
    default_retry_delay=60,
)
def create_recurring_reminders(self, db: Session, conversation_id: int):
    """
    为会话创建周期性用药提醒
    
    根据会话中的用药建议，创建周期性提醒任务
    
    Args:
        db: 数据库会话
        conversation_id: 会话ID
    """
    try:
        logger.info(f"创建周期性用药提醒 - 会话ID: {conversation_id}")
        
        # TODO: 实现周期性提醒创建逻辑
        # 1. 查询会话中的用药建议
        # 2. 解析用药频率和时间
        # 3. 创建周期性提醒记录
        # 4. 调度提醒任务
        
        # 示例代码结构：
        # conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        # medications = extract_medications_from_conversation(conversation)
        # for medication in medications:
        #     reminders = create_reminders_for_medication(medication, conversation.patient_id)
        #     for reminder in reminders:
        #         ReminderService.create_reminder(reminder, db)
        #         schedule_reminder_task(reminder.id)
        
        logger.info(f"周期性用药提醒创建完成 - 会话ID: {conversation_id}")
        return {"status": "success", "conversation_id": conversation_id}
        
    except Exception as e:
        logger.error(f"创建周期性用药提醒失败 - 会话ID: {conversation_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


# 导出
__all__ = [
    "check_and_send_reminders",
    "send_reminder",
    "create_recurring_reminders",
]

