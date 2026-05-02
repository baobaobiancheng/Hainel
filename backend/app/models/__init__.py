"""
数据库模型
定义所有数据库模型类
"""
from app.models.base import BaseModel
from app.models.user import User
from app.models.conversation import (
    Conversation,
    ConversationStatus,
    ComplexityLevel,
    CollaborationMode,
)
from app.models.message import (
    Message,
    MessageType,
    MessageRole,
)
from app.models.medical_record import (
    MedicalRecord,
    MedicalRecordStatus,
)
from app.models.reminder import Reminder
from app.models.token_usage_log import TokenUsageLog
from app.models.enums import ReminderType, ReminderStatus, ReminderFrequency

# 导出所有模型
__all__ = [
    # 基础模型
    "BaseModel",
    # 用户模型
    "User",
    # 会话模型
    "Conversation",
    "ConversationStatus",
    "ComplexityLevel",
    "CollaborationMode",
    # 消息模型
    "Message",
    "MessageType",
    "MessageRole",
    # 病历模型
    "MedicalRecord",
    "MedicalRecordStatus",
    # 提醒模型
    "Reminder",
    "TokenUsageLog",
    "ReminderType",
    "ReminderStatus",
    "ReminderFrequency",
]

