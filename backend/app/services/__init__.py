"""
业务服务层
提供各种业务逻辑处理服务
"""
from app.services.user_service import UserService, user_service
from app.services.conversation_service import ConversationService, conversation_service
from app.services.message_service import MessageService, message_service
from app.services.medical_record_service import MedicalRecordService, medical_record_service
from app.services.doctor_service import DoctorService, doctor_service

# 导出所有服务
__all__ = [
    # 用户服务
    "UserService",
    "user_service",
    # 会话服务
    "ConversationService",
    "conversation_service",
    # 消息服务
    "MessageService",
    "message_service",
    # 病历服务
    "MedicalRecordService",
    "medical_record_service",
    # 医生服务
    "DoctorService",
    "doctor_service",
]

