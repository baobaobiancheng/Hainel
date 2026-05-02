"""
通知任务模块
处理系统通知相关的异步任务
"""
import asyncio
from datetime import datetime
from typing import List, Optional, Dict, Any
from celery import Task
from sqlalchemy.orm import Session

from app.tasks.celery_app import celery_app
from app.database.session import get_db_session
from app.api.v1.long_polling import poll_manager
from app.services.conversation_service import ConversationService
from app.services.message_service import MessageService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_async(coro):
    """
    在同步上下文中运行异步函数
    
    Args:
        coro: 协程对象
    
    Returns:
        协程的返回值
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        # 如果事件循环已经在运行，使用asyncio.create_task
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return loop.run_until_complete(coro)


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
    name="app.tasks.notification_tasks.send_message_notification",
    max_retries=3,
    default_retry_delay=10,
)
def send_message_notification(
    self,
    db: Session,
    message_id: int,
    conversation_id: int,
    user_ids: Optional[List[int]] = None,
):
    """
    发送消息通知

    通过长轮询向用户发送新消息通知

    Args:
        db: 数据库会话
        message_id: 消息ID
        conversation_id: 会话ID
        user_ids: 要通知的用户ID列表（如果为None则通知会话中的所有用户）
    """
    try:
        logger.info(f"发送消息通知 - 消息ID: {message_id}, 会话ID: {conversation_id}")

        # 获取消息信息
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            logger.warning(f"消息不存在 - 消息ID: {message_id}")
            return {"status": "failed", "reason": "message_not_found"}

        # 获取会话信息
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            logger.warning(f"会话不存在 - 会话ID: {conversation_id}")
            return {"status": "failed", "reason": "conversation_not_found"}

        # 触发轮询通知
        try:
            run_async(poll_manager.notify_new_message(conversation_id))
        except Exception as e:
            logger.error(f"触发轮询通知失败: {e}")

        logger.info(f"消息通知发送完成 - 会话ID: {conversation_id}")
        return {
            "status": "success",
            "message_id": message_id,
            "conversation_id": conversation_id,
        }

    except Exception as e:
        logger.error(f"发送消息通知失败 - 消息ID: {message_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.notification_tasks.send_conversation_status_notification",
    max_retries=2,
    default_retry_delay=10,
)
def send_conversation_status_notification(
    self,
    db: Session,
    conversation_id: int,
    status: str,
    message: Optional[str] = None,
):
    """
    发送会话状态通知

    通知用户会话状态变化（如会话开始、结束、转诊等）

    Args:
        db: 数据库会话
        conversation_id: 会话ID
        status: 状态（如 "started", "ended", "transferred"）
        message: 附加消息（可选）
    """
    try:
        logger.info(f"发送会话状态通知 - 会话ID: {conversation_id}, 状态: {status}")

        # 获取会话信息
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            logger.warning(f"会话不存在 - 会话ID: {conversation_id}")
            return {"status": "failed", "reason": "conversation_not_found"}

        # 触发轮询通知
        try:
            run_async(poll_manager.notify_new_message(conversation_id))
        except Exception as e:
            logger.error(f"触发轮询通知失败: {e}")

        logger.info(f"会话状态通知发送完成 - 会话ID: {conversation_id}")
        return {
            "status": "success",
            "conversation_id": conversation_id,
        }

    except Exception as e:
        logger.error(f"发送会话状态通知失败 - 会话ID: {conversation_id}: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.notification_tasks.cleanup_expired_conversations",
    max_retries=1,
    default_retry_delay=300,
)
def cleanup_expired_conversations(self, db: Session):
    """
    清理过期会话
    
    清理超过超时时间的会话，通常作为定时任务运行
    
    Args:
        db: 数据库会话
    """
    try:
        logger.info("开始清理过期会话")
        
        # TODO: 实现会话清理逻辑
        # 1. 查询超时的会话
        # 2. 更新会话状态为已结束
        # 3. 发送通知给用户
        # 4. 可选：归档会话数据
        
        # 示例代码结构：
        # timeout_minutes = settings.CONVERSATION_TIMEOUT_MINUTES
        # expired_conversations = ConversationService.get_expired_conversations(
        #     timeout_minutes=timeout_minutes,
        #     db=db
        # )
        # 
        # for conversation in expired_conversations:
        #     ConversationService.end_conversation(conversation.id, db)
        #     send_conversation_status_notification.delay(
        #         conversation_id=conversation.id,
        #         status="expired",
        #         message="会话已超时，自动结束"
        #     )
        
        logger.info("过期会话清理完成")
        return {
            "status": "success",
            "cleaned_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"清理过期会话失败: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.notification_tasks.archive_old_medical_records",
    max_retries=1,
    default_retry_delay=300,
)
def archive_old_medical_records(self, db: Session):
    """
    归档旧病历
    
    将超过归档天数的病历标记为已归档，通常作为定时任务运行
    
    Args:
        db: 数据库会话
    """
    try:
        logger.info("开始归档旧病历")
        
        # TODO: 实现病历归档逻辑
        # 1. 查询超过归档天数的病历
        # 2. 标记为已归档
        # 3. 可选：移动到归档存储
        
        # 示例代码结构：
        # archive_days = settings.MEDICAL_RECORD_AUTO_ARCHIVE_DAYS
        # old_records = MedicalRecordService.get_records_to_archive(
        #     days=archive_days,
        #     db=db
        # )
        # 
        # for record in old_records:
        #     MedicalRecordService.archive_record(record.id, db)
        
        logger.info("旧病历归档完成")
        return {
            "status": "success",
            "archived_at": datetime.now().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"归档旧病历失败: {e}", exc_info=True)
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    name="app.tasks.notification_tasks.send_batch_notifications",
    max_retries=2,
    default_retry_delay=30,
)
def send_batch_notifications(
    self,
    db: Session,
    notifications: List[Dict[str, Any]],
):
    """
    批量发送通知

    批量发送多个通知，提高效率

    Args:
        db: 数据库会话
        notifications: 通知列表，每个通知包含 type, user_id, data 等字段
    """
    try:
        logger.info(f"开始批量发送通知 - 数量: {len(notifications)}")

        sent_count = 0
        failed_count = 0

        for notification in notifications:
            try:
                notification_type = notification.get("type")
                conversation_id = notification.get("conversation_id")

                if not conversation_id:
                    logger.warning(f"通知缺少会话ID: {notification}")
                    failed_count += 1
                    continue

                # 根据类型发送不同的通知
                if notification_type == "message":
                    send_message_notification.delay(
                        message_id=notification.get("message_id"),
                        conversation_id=conversation_id,
                        user_ids=notification.get("user_ids"),
                    )
                elif notification_type == "conversation_status":
                    send_conversation_status_notification.delay(
                        conversation_id=conversation_id,
                        status=notification.get("status"),
                        message=notification.get("message"),
                    )
                else:
                    # 通用通知 - 触发轮询
                    try:
                        run_async(poll_manager.notify_new_message(conversation_id))
                    except Exception as e:
                        logger.error(f"触发轮询通知失败: {e}")

                sent_count += 1

            except Exception as e:
                logger.error(f"发送单个通知失败: {e}")
                failed_count += 1

        logger.info(f"批量通知发送完成 - 成功: {sent_count}, 失败: {failed_count}")
        return {
            "status": "success",
            "total": len(notifications),
            "sent": sent_count,
            "failed": failed_count,
        }

    except Exception as e:
        logger.error(f"批量发送通知失败: {e}", exc_info=True)
        raise self.retry(exc=e)


# 导出
__all__ = [
    "send_message_notification",
    "send_conversation_status_notification",
    "cleanup_expired_conversations",
    "archive_old_medical_records",
    "send_batch_notifications",
]

