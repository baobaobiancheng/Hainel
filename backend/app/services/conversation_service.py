"""
会话服务
提供会话相关的业务逻辑处理
"""
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any, Set
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc

from app.models.conversation import (
    Conversation,
    ConversationStatus,
    ComplexityLevel,
    CollaborationMode,
)
from app.models.user import User
from app.core.permissions import Role
from app.models.message import Message, MessageRole, MessageType
from app.models.medical_record import MedicalRecord
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationStatusUpdate,
    ConversationComplexityUpdate,
    calculate_age_from_birth_date,
)
from app.core.exceptions import (
    NotFoundException,
    BusinessException,
    ValidationException,
)
from app.database.session import get_session
from app.utils.logger import get_logger

logger = get_logger(__name__)


async def _push_status_to_patient(conversation_id: int, patient_id: int, status: str, message: str, data: dict = None):
    """
    异步推送状态给患者

    Args:
        conversation_id: 会话ID
        patient_id: 患者ID
        status: 状态
        message: 状态消息
        data: 附加数据
    """
    try:
        from app.api.v1.websocket import push_status_update
        await push_status_update(
            conversation_id=conversation_id,
            patient_id=patient_id,
            status=status,
            message=message,
            data=data
        )
    except Exception as e:
        logger.error(f"推送状态失败: {e}")


class ConversationService:
    """会话服务类"""
    
    @staticmethod
    def create_conversation(conversation_data: ConversationCreate, db: Session) -> Conversation:
        """
        创建新会话
        
        Args:
            conversation_data: 会话创建数据
            db: 数据库会话
        
        Returns:
            创建的会话对象
        
        Raises:
            NotFoundException: 患者或医生不存在
        """
        # 验证患者是否存在
        patient = db.query(User).filter(User.id == conversation_data.patient_id).first()
        if not patient:
            raise NotFoundException(f"患者 ID {conversation_data.patient_id} 不存在")
        
        # 验证医生是否存在（如果指定了医生）
        if conversation_data.doctor_id:
            doctor = db.query(User).filter(User.id == conversation_data.doctor_id).first()
            if not doctor:
                raise NotFoundException(f"医生 ID {conversation_data.doctor_id} 不存在")
        
        # 创建会话对象
        conversation = Conversation(
            patient_id=conversation_data.patient_id,
            doctor_id=conversation_data.doctor_id,
            title=conversation_data.title,
            chief_complaint=conversation_data.chief_complaint,
            status=ConversationStatus.PENDING,
            extra_metadata=conversation_data.extra_metadata,
        )
        
        db.add(conversation)
        db.commit()
        db.refresh(conversation)

        logger.info(f"创建会话成功: ID {conversation.id}, 患者 ID {conversation.patient_id}")

        # 异步推送状态给患者
        asyncio.create_task(_push_status_to_patient(
            conversation_id=conversation.id,
            patient_id=conversation.patient_id,
            status="submitted",
            message="已提交，正在等待智能分析..."
        ))

        return conversation
    
    @staticmethod
    def get_conversation_by_id(conversation_id: int, db: Session) -> Optional[Conversation]:
        """
        根据ID获取会话
        
        Args:
            conversation_id: 会话ID
            db: 数据库会话
        
        Returns:
            会话对象，如果不存在返回None
        """
        return db.query(Conversation).filter(Conversation.id == conversation_id).first()
    
    @staticmethod
    def update_conversation(
        conversation_id: int,
        conversation_data: ConversationUpdate,
        db: Session,
    ) -> Conversation:
        """
        更新会话信息
        
        Args:
            conversation_id: 会话ID
            conversation_data: 会话更新数据
            db: 数据库会话
        
        Returns:
            更新后的会话对象
        
        Raises:
            NotFoundException: 会话不存在
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 如果更新医生ID，验证医生是否存在
        if conversation_data.doctor_id is not None:
            doctor = db.query(User).filter(User.id == conversation_data.doctor_id).first()
            if not doctor:
                raise NotFoundException(f"医生 ID {conversation_data.doctor_id} 不存在")
        
        # 更新字段
        update_dict = conversation_data.model_dump(exclude_unset=True)
        
        # 如果更新状态，需要特殊处理
        if "status" in update_dict:
            status_str = update_dict["status"]
            try:
                update_dict["status"] = ConversationStatus(status_str)
            except ValueError:
                raise ValidationException(f"无效的会话状态: {status_str}")
        
        conversation.update_from_dict(update_dict)
        db.commit()
        db.refresh(conversation)
        
        logger.info(f"更新会话成功: ID {conversation.id}")
        return conversation
    
    @staticmethod
    def update_conversation_status(
        conversation_id: int,
        status_data: ConversationStatusUpdate,
        db: Session,
    ) -> Conversation:
        """
        更新会话状态
        
        Args:
            conversation_id: 会话ID
            status_data: 状态更新数据
            db: 数据库会话
        
        Returns:
            更新后的会话对象
        
        Raises:
            NotFoundException: 会话不存在
            ValidationException: 无效的状态值
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        try:
            new_status = ConversationStatus(status_data.status)
        except ValueError:
            raise ValidationException(f"无效的会话状态: {status_data.status}")
        
        # 根据状态执行相应操作
        if new_status == ConversationStatus.ACTIVE:
            conversation.mark_as_active()
        elif new_status == ConversationStatus.COMPLETED:
            conversation.mark_as_completed()
        elif new_status == ConversationStatus.CANCELLED:
            conversation.mark_as_cancelled()
        else:
            conversation.status = new_status
        
        db.commit()
        db.refresh(conversation)

        logger.info(f"更新会话状态成功: ID {conversation.id}, 状态: {new_status.value}")

        # 推送状态给患者
        status_messages = {
            ConversationStatus.ACTIVE: "智能分析结果已生成，您可以继续补充症状或追问",
            ConversationStatus.PENDING: "等待处理中",
            ConversationStatus.PAUSED: "会话已暂停",
            ConversationStatus.COMPLETED: "诊断已完成",
            ConversationStatus.CANCELLED: "会话已取消",
        }

        push_message = status_messages.get(new_status, f"状态已更新: {new_status.value}")
        push_status = "completed" if new_status == ConversationStatus.ACTIVE else new_status.value
        asyncio.create_task(_push_status_to_patient(
            conversation_id=conversation.id,
            patient_id=conversation.patient_id,
            status=push_status,
            message=push_message
        ))

        return conversation
    
    @staticmethod
    def update_complexity(
        conversation_id: int,
        complexity_data: ConversationComplexityUpdate,
        db: Session,
    ) -> Conversation:
        """
        更新会话复杂度评估结果
        
        Args:
            conversation_id: 会话ID
            complexity_data: 复杂度更新数据
            db: 数据库会话
        
        Returns:
            更新后的会话对象
        
        Raises:
            NotFoundException: 会话不存在
            ValidationException: 无效的枚举值
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        try:
            complexity_level = ComplexityLevel(complexity_data.complexity_level)
            collaboration_mode = CollaborationMode(complexity_data.collaboration_mode)
        except ValueError as e:
            raise ValidationException(f"无效的枚举值: {e}")
        
        conversation.complexity_level = complexity_level
        conversation.complexity_score = complexity_data.complexity_score
        conversation.collaboration_mode = collaboration_mode
        conversation.agent_ids = complexity_data.agent_ids
        conversation.agent_count = len(complexity_data.agent_ids) if complexity_data.agent_ids else 1
        
        db.commit()
        db.refresh(conversation)

        logger.info(
            f"更新会话复杂度成功: ID {conversation.id}, "
            f"复杂度: {complexity_level.value}, 模式: {collaboration_mode.value}"
        )

        # 推送智能分析完成状态
        asyncio.create_task(_push_status_to_patient(
            conversation_id=conversation.id,
            patient_id=conversation.patient_id,
            status="completed",
            message="智能分析结果已生成，您可以继续补充症状或追问",
            data={
                "complexity_level": complexity_level.value,
                "collaboration_mode": collaboration_mode.value
            }
        ))

        return conversation
    
    @staticmethod
    def list_conversations(
        skip: int = 0,
        limit: int = 100,
        patient_id: Optional[int] = None,
        doctor_id: Optional[int] = None,
        status: Optional[ConversationStatus] = None,
        complexity_level: Optional[ComplexityLevel] = None,
        collaboration_mode: Optional[CollaborationMode] = None,
        include_total: bool = True,
        db: Session = None,
    ) -> tuple[List[Conversation], int, bool]:
        """
        获取会话列表

        Args:
            skip: 跳过的记录数
            limit: 返回的记录数
            patient_id: 患者ID过滤
            doctor_id: 医生ID过滤
            status: 状态过滤
            complexity_level: 复杂度级别过滤
            collaboration_mode: 协作模式过滤
            include_total: 是否计算总数
            db: 数据库会话

        Returns:
            (会话列表, 总数量, 是否有下一页)
        """
        if db is None:
            with get_session() as session:
                return ConversationService.list_conversations(
                    skip, limit, patient_id, doctor_id, status,
                    complexity_level, collaboration_mode, include_total, session
                )

        query = db.query(Conversation)

        # 患者过滤
        if patient_id:
            query = query.filter(Conversation.patient_id == patient_id)

        # 医生过滤
        if doctor_id:
            query = query.filter(Conversation.doctor_id == doctor_id)

        # 状态过滤
        if status:
            query = query.filter(Conversation.status == status)

        # 复杂度过滤
        if complexity_level:
            query = query.filter(Conversation.complexity_level == complexity_level)

        # 协作模式过滤
        if collaboration_mode:
            query = query.filter(Conversation.collaboration_mode == collaboration_mode)

        # 获取总数
        total = query.count() if include_total else 0

        # 分页，按创建时间倒序
        conversations = (
            query.order_by(desc(Conversation.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

        has_next = (skip + limit) < total if include_total else len(conversations) == limit

        return conversations, total, has_next
    
    @staticmethod
    def assign_doctor(
        conversation_id: int,
        doctor_id: int,
        db: Session,
    ) -> Conversation:
        """
        分配医生到会话
        
        Args:
            conversation_id: 会话ID
            doctor_id: 医生ID
            db: 数据库会话
        
        Returns:
            更新后的会话对象
        
        Raises:
            NotFoundException: 会话或医生不存在
            BusinessException: 会话已有医生或状态不允许分配
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 验证被分配用户存在且角色为医生
        doctor = db.query(User).filter(User.id == doctor_id).first()
        if not doctor:
            raise NotFoundException(f"用户 ID {doctor_id} 不存在")
        if doctor.role != Role.DOCTOR:
            raise ValidationException("只能指定医生账号进行分配")
        
        # 检查会话是否已有医生
        if conversation.doctor_id:
            if conversation.doctor_id == doctor_id:
                logger.warning(f"会话 {conversation_id} 已分配给该医生")
                return conversation
            else:
                raise BusinessException("会话已分配给其他医生")
        
        # 分配医生
        conversation.doctor_id = doctor_id
        db.commit()
        db.refresh(conversation)

        logger.info(f"分配医生成功: 会话 ID {conversation_id}, 医生 ID {doctor_id}")

        # 推送医生开始处理状态给患者
        asyncio.create_task(_push_status_to_patient(
            conversation_id=conversation.id,
            patient_id=conversation.patient_id,
            status="reviewing",
            message="医生正在审核..."
        ))

        return conversation
    
    @staticmethod
    def increment_message_count(conversation_id: int, db: Session) -> Conversation:
        """
        增加会话消息计数
        
        Args:
            conversation_id: 会话ID
            db: 数据库会话
        
        Returns:
            更新后的会话对象
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if conversation:
            conversation.message_count += 1
            conversation.last_message_at = datetime.utcnow()
            db.commit()
            db.refresh(conversation)
        return conversation
    
    @staticmethod
    def increment_round_count(conversation_id: int, db: Session) -> Conversation:
        """
        增加会话对话轮次计数
        
        Args:
            conversation_id: 会话ID
            db: 数据库会话
        
        Returns:
            更新后的会话对象
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if conversation:
            conversation.round_count += 1
            db.commit()
            db.refresh(conversation)
        return conversation
    
    @staticmethod
    def get_conversation_statistics(conversation_id: int, db: Session) -> Dict[str, Any]:
        """
        获取会话统计信息
        
        Args:
            conversation_id: 会话ID
            db: 数据库会话
        
        Returns:
            统计信息字典
        
        Raises:
            NotFoundException: 会话不存在
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 统计消息数量
        message_count = (
            db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .count()
        )
        
        # 统计用户消息数量
        user_message_count = (
            db.query(Message)
            .filter(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.role == MessageRole.USER
                )
            )
            .count()
        )
        
        # 统计智能体消息数量
        assistant_message_count = (
            db.query(Message)
            .filter(
                and_(
                    Message.conversation_id == conversation_id,
                    Message.role == MessageRole.ASSISTANT
                )
            )
            .count()
        )
        
        stats = {
            "conversation_id": conversation_id,
            "message_count": message_count,
            "user_message_count": user_message_count,
            "assistant_message_count": assistant_message_count,
            "round_count": conversation.round_count,
            "status": conversation.status.value if conversation.status else None,
            "complexity_level": conversation.complexity_level.value if conversation.complexity_level else None,
            "collaboration_mode": conversation.collaboration_mode.value if conversation.collaboration_mode else None,
        }
        
        return stats
    
    @staticmethod
    def delete_conversation(conversation_id: int, db: Session) -> bool:
        """
        删除会话
        
        Args:
            conversation_id: 会话ID
            db: 数据库会话
        
        Returns:
            是否删除成功
        
        Raises:
            NotFoundException: 会话不存在
        """
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        db.delete(conversation)
        db.commit()
        
        logger.info(f"删除会话成功: ID {conversation_id}")
        return True


# 创建全局服务实例
def _conversation_normalize_metadata(data: Optional[Any]) -> Dict[str, Any]:
    if isinstance(data, dict):
        return data

    extra_metadata = getattr(data, "extra_metadata", None)
    if isinstance(extra_metadata, dict):
        return extra_metadata

    metadata = getattr(data, "metadata", None)
    if isinstance(metadata, dict):
        return metadata

    return {}


def _conversation_serialize_report(message: Message) -> Dict[str, Any]:
    metadata = _conversation_normalize_metadata(message.extra_metadata)
    ocr_result = _conversation_normalize_metadata(metadata.get("ocr_result"))
    return {
        "message_id": message.id,
        "file_name": message.file_name,
        "file_type": metadata.get("file_type") or message.file_type,
        "report_type": metadata.get("report_type"),
        "ocr_text": ocr_result.get("text") or "",
    }


def _conversation_is_primary_diagnosis_message(message: Message) -> bool:
    metadata = _conversation_normalize_metadata(message.extra_metadata)
    return metadata.get("analysis_type") == "智能诊断"


def _conversation_is_fallback_diagnosis_message(message: Message) -> bool:
    metadata = _conversation_normalize_metadata(message.extra_metadata)
    return (
        bool(metadata.get("action_checklist")) or
        bool(metadata.get("triage")) or
        bool(metadata.get("red_flags"))
    )


def _conversation_select_latest_diagnosis_message(messages: List[Message]) -> Optional[Message]:
    for message in messages:
        if _conversation_is_primary_diagnosis_message(message):
            return message
    for message in messages:
        if _conversation_is_fallback_diagnosis_message(message):
            return message
    return None


def _conversation_get_diagnosis_context(conversation_id: int, db: Session) -> Dict[str, Any]:
    conversation = ConversationService.get_conversation_by_id(conversation_id, db)
    if not conversation:
        raise NotFoundException(f"浼氳瘽 ID {conversation_id} 涓嶅瓨鍦?")

    patient = db.query(User).filter(User.id == conversation.patient_id).first()
    conversation_metadata = _conversation_normalize_metadata(conversation.extra_metadata)
    health_profile = patient.health_profile if patient and isinstance(patient.health_profile, dict) else {}
    patient_name = patient.full_name or patient.username if patient else None
    patient_gender = health_profile.get("gender")
    patient_age = calculate_age_from_birth_date(health_profile.get("birth_date"))

    assistant_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
        )
        .order_by(desc(Message.created_at), desc(Message.id))
        .all()
    )
    latest_diagnosis_message = _conversation_select_latest_diagnosis_message(assistant_messages)

    latest_diagnosis = None
    linked_reports: List[Dict[str, Any]] = []
    triage = conversation_metadata.get("triage")

    if latest_diagnosis_message:
        diagnosis_metadata = _conversation_normalize_metadata(latest_diagnosis_message.extra_metadata)
        latest_diagnosis = {
            "message_id": latest_diagnosis_message.id,
            "content": latest_diagnosis_message.content,
            "difficulty": diagnosis_metadata.get("difficulty"),
            "agents_used": diagnosis_metadata.get("agents_used"),
            "red_flags": diagnosis_metadata.get("red_flags") or [],
            "action_checklist": diagnosis_metadata.get("action_checklist"),
            "kg_context": diagnosis_metadata.get("kg_context"),
            "triage": diagnosis_metadata.get("triage"),
            "team_recruitment": diagnosis_metadata.get("team_recruitment"),
            "expert_opinions": diagnosis_metadata.get("expert_opinions") or [],
            "mdt_plan": diagnosis_metadata.get("mdt_plan"),
            "team_reports": diagnosis_metadata.get("team_reports") or [],
            "created_at": latest_diagnosis_message.created_at,
        }
        triage = triage or diagnosis_metadata.get("triage")
        raw_linked_reports = diagnosis_metadata.get("linked_reports")
        if isinstance(raw_linked_reports, list):
            linked_reports = [
                {
                    "message_id": item.get("message_id"),
                    "file_name": item.get("file_name"),
                    "file_type": item.get("file_type"),
                    "report_type": item.get("report_type"),
                    "ocr_text": item.get("ocr_text") or "",
                }
                for item in raw_linked_reports
                if isinstance(item, dict)
            ]

    if not linked_reports:
        report_messages = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.message_type == MessageType.FILE,
            )
            .order_by(desc(Message.created_at), desc(Message.id))
            .limit(3)
            .all()
        )
        report_messages = [
            message
            for message in report_messages
            if getattr(message, "message_type", None) in {MessageType.FILE, "file"}
        ][:3]
        linked_reports = [_conversation_serialize_report(message) for message in report_messages]

    medical_records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.conversation_id == conversation_id)
        .order_by(desc(MedicalRecord.updated_at), desc(MedicalRecord.id))
        .all()
    )

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status.value if conversation.status else None,
            "chief_complaint": conversation.chief_complaint,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
        "patient": {
            "id": conversation.patient_id,
            "name": patient_name,
            "gender": patient_gender,
            "age": patient_age,
        },
        "health_profile": health_profile,
        "structured_intake": conversation_metadata.get("structured_intake") or {},
        "triage": triage,
        "linked_reports": linked_reports,
        "latest_diagnosis": latest_diagnosis,
        "medical_records": [
            {
                "id": record.id,
                "title": record.title,
                "status": record.status.value if record.status else None,
                "updated_at": record.updated_at,
            }
            for record in medical_records
        ],
    }


def _conversation_serialize_report(message: Message) -> Dict[str, Any]:
    metadata = _conversation_normalize_metadata(message)
    ocr_result = _conversation_normalize_metadata(metadata.get("ocr_result"))
    return {
        "message_id": message.id,
        "file_name": message.file_name,
        "file_type": metadata.get("file_type") or message.file_type,
        "report_type": metadata.get("report_type"),
        "ocr_text": ocr_result.get("text") or "",
    }


def _conversation_is_primary_diagnosis_message(message: Message) -> bool:
    metadata = _conversation_normalize_metadata(message)
    analysis_type = metadata.get("analysis_type")
    return analysis_type in {"智能诊断", "鏅鸿兘璇婃柇"}


def _conversation_is_fallback_diagnosis_message(message: Message) -> bool:
    metadata = _conversation_normalize_metadata(message)
    return (
        bool(metadata.get("action_checklist")) or
        bool(metadata.get("triage")) or
        bool(metadata.get("red_flags"))
    )


def _conversation_get_diagnosis_context(conversation_id: int, db: Session) -> Dict[str, Any]:
    conversation = ConversationService.get_conversation_by_id(conversation_id, db)
    if not conversation:
        raise NotFoundException(f"娴兼俺鐦?ID {conversation_id} 娑撳秴鐡ㄩ崷?")

    patient = db.query(User).filter(User.id == conversation.patient_id).first()
    conversation_metadata = _conversation_normalize_metadata(conversation)
    health_profile = patient.health_profile if patient and isinstance(patient.health_profile, dict) else {}
    patient_name = patient.full_name or patient.username if patient else None
    patient_gender = health_profile.get("gender")
    patient_age = calculate_age_from_birth_date(health_profile.get("birth_date"))

    assistant_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
        )
        .order_by(desc(Message.created_at), desc(Message.id))
        .all()
    )
    latest_diagnosis_message = _conversation_select_latest_diagnosis_message(assistant_messages)

    latest_diagnosis = None
    linked_reports: List[Dict[str, Any]] = []
    triage = conversation_metadata.get("triage")

    if latest_diagnosis_message:
        diagnosis_metadata = _conversation_normalize_metadata(latest_diagnosis_message)
        latest_diagnosis = {
            "message_id": latest_diagnosis_message.id,
            "content": latest_diagnosis_message.content,
            "difficulty": diagnosis_metadata.get("difficulty"),
            "agents_used": diagnosis_metadata.get("agents_used"),
            "red_flags": diagnosis_metadata.get("red_flags") or [],
            "action_checklist": diagnosis_metadata.get("action_checklist"),
            "kg_context": diagnosis_metadata.get("kg_context"),
            "triage": diagnosis_metadata.get("triage"),
            "team_recruitment": diagnosis_metadata.get("team_recruitment"),
            "expert_opinions": diagnosis_metadata.get("expert_opinions") or [],
            "mdt_plan": diagnosis_metadata.get("mdt_plan"),
            "team_reports": diagnosis_metadata.get("team_reports") or [],
            "created_at": latest_diagnosis_message.created_at,
        }
        triage = triage or diagnosis_metadata.get("triage")
        raw_linked_reports = diagnosis_metadata.get("linked_reports")
        if isinstance(raw_linked_reports, list):
            linked_reports = [
                {
                    "message_id": item.get("message_id"),
                    "file_name": item.get("file_name"),
                    "file_type": item.get("file_type"),
                    "report_type": item.get("report_type"),
                    "ocr_text": item.get("ocr_text") or "",
                }
                for item in raw_linked_reports
                if isinstance(item, dict)
            ]

    if not linked_reports:
        report_messages = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.message_type == MessageType.FILE,
            )
            .order_by(desc(Message.created_at), desc(Message.id))
            .limit(3)
            .all()
        )
        linked_reports = [_conversation_serialize_report(message) for message in report_messages]

    medical_records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.conversation_id == conversation_id)
        .order_by(desc(MedicalRecord.updated_at), desc(MedicalRecord.id))
        .all()
    )

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status.value if conversation.status else None,
            "chief_complaint": conversation.chief_complaint,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
        "patient": {
            "id": conversation.patient_id,
            "name": patient_name,
            "gender": patient_gender,
            "age": patient_age,
        },
        "health_profile": health_profile,
        "structured_intake": conversation_metadata.get("structured_intake") or {},
        "triage": triage,
        "linked_reports": linked_reports,
        "latest_diagnosis": latest_diagnosis,
        "medical_records": [
            {
                "id": record.id,
                "title": record.title,
                "status": record.status.value if record.status else None,
                "updated_at": record.updated_at,
            }
            for record in medical_records
        ],
    }


def _conversation_get_diagnosis_context(conversation_id: int, db: Session) -> Dict[str, Any]:
    conversation = ConversationService.get_conversation_by_id(conversation_id, db)
    if not conversation:
        raise NotFoundException(f"娴兼俺鐦?ID {conversation_id} 娑撳秴鐡ㄩ崷?")

    patient = db.query(User).filter(User.id == conversation.patient_id).first()
    conversation_metadata = _conversation_normalize_metadata(conversation)
    health_profile = patient.health_profile if patient and isinstance(patient.health_profile, dict) else {}
    patient_name = patient.full_name or patient.username if patient else None
    patient_gender = health_profile.get("gender")
    patient_age = calculate_age_from_birth_date(health_profile.get("birth_date"))

    assistant_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
        )
        .order_by(desc(Message.created_at), desc(Message.id))
        .all()
    )
    latest_diagnosis_message = _conversation_select_latest_diagnosis_message(assistant_messages)

    latest_diagnosis = None
    linked_reports: List[Dict[str, Any]] = []
    triage = conversation_metadata.get("triage")

    if latest_diagnosis_message:
        diagnosis_metadata = _conversation_normalize_metadata(latest_diagnosis_message)
        latest_diagnosis = {
            "message_id": latest_diagnosis_message.id,
            "content": latest_diagnosis_message.content,
            "difficulty": diagnosis_metadata.get("difficulty"),
            "agents_used": diagnosis_metadata.get("agents_used"),
            "red_flags": diagnosis_metadata.get("red_flags") or [],
            "action_checklist": diagnosis_metadata.get("action_checklist"),
            "kg_context": diagnosis_metadata.get("kg_context"),
            "triage": diagnosis_metadata.get("triage"),
            "team_recruitment": diagnosis_metadata.get("team_recruitment"),
            "expert_opinions": diagnosis_metadata.get("expert_opinions") or [],
            "mdt_plan": diagnosis_metadata.get("mdt_plan"),
            "team_reports": diagnosis_metadata.get("team_reports") or [],
            "created_at": latest_diagnosis_message.created_at,
        }
        triage = triage or diagnosis_metadata.get("triage")
        raw_linked_reports = diagnosis_metadata.get("linked_reports")
        if isinstance(raw_linked_reports, list):
            linked_reports = [
                {
                    "message_id": item.get("message_id"),
                    "file_name": item.get("file_name"),
                    "file_type": item.get("file_type"),
                    "report_type": item.get("report_type"),
                    "ocr_text": item.get("ocr_text") or "",
                }
                for item in raw_linked_reports
                if isinstance(item, dict)
            ]

    if not linked_reports:
        report_messages = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.message_type == MessageType.FILE,
            )
            .order_by(desc(Message.created_at), desc(Message.id))
            .all()
        )
        report_messages = [
            message
            for message in report_messages
            if getattr(message, "message_type", None) in {MessageType.FILE, "file"}
        ][:3]
        linked_reports = [_conversation_serialize_report(message) for message in report_messages]

    medical_records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.conversation_id == conversation_id)
        .order_by(desc(MedicalRecord.updated_at), desc(MedicalRecord.id))
        .all()
    )

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status.value if conversation.status else None,
            "chief_complaint": conversation.chief_complaint,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
        "patient": {
            "id": conversation.patient_id,
            "name": patient_name,
            "gender": patient_gender,
            "age": patient_age,
        },
        "health_profile": health_profile,
        "structured_intake": conversation_metadata.get("structured_intake") or {},
        "triage": triage,
        "linked_reports": linked_reports,
        "latest_diagnosis": latest_diagnosis,
        "medical_records": [
            {
                "id": record.id,
                "title": record.title,
                "status": record.status.value if record.status else None,
                "updated_at": record.updated_at,
            }
            for record in medical_records
        ],
    }


ConversationService._normalize_metadata = staticmethod(_conversation_normalize_metadata)
ConversationService._serialize_report = staticmethod(_conversation_serialize_report)
ConversationService.select_latest_diagnosis_message = staticmethod(_conversation_select_latest_diagnosis_message)
ConversationService.get_diagnosis_context = staticmethod(_conversation_get_diagnosis_context)


conversation_service = ConversationService()


# 导出
__all__ = ["ConversationService", "conversation_service"]


_KG_REL_LABEL_MAP = {
    "has_symptom": "症状",
    "acompany_with": "伴随问题",
    "common_drug": "常用药物",
    "recommand_drug": "推荐药物",
    "need_check": "检查",
    "do_eat": "宜吃",
    "no_eat": "忌吃",
    "recommand_eat": "推荐饮食",
    "belongs_to": "相关科室",
    "drugs_of": "药物",
    "治疗": "治疗",
    "相关症状": "症状",
    "检查": "检查",
    "临床表现": "症状",
    "并发症": "伴随问题",
}

_KG_GROUP_TITLES = {
    "symptom": "症状与体征",
    "exam": "检查与化验",
    "drug": "药物相关",
    "food_recommended": "宜吃与推荐饮食",
    "food_avoid": "饮食禁忌",
    "department": "相关科室",
    "complication": "伴随问题",
    "treatment": "治疗建议",
    "other": "其他关联知识",
}

_KG_GROUP_ORDER = [
    "symptom",
    "exam",
    "drug",
    "food_recommended",
    "food_avoid",
    "department",
    "complication",
    "treatment",
    "other",
]

_KG_TARGET_CATEGORY_MAP = {
    "Symptom": "symptom",
    "Exam": "exam",
    "Drug": "drug",
    "Department": "department",
    "Food": "food",
    "Treatment": "treatment",
    "Disease": "disease",
    "BodyPart": "body_part",
}

_STRUCTURED_INTAKE_LABELS = {
    "main_symptom": "主要症状",
    "duration": "持续时间",
    "accompanying_symptoms": "伴随症状",
    "pain_location": "疼痛部位",
    "pain_level": "疼痛程度",
    "fever": "发热情况",
    "recent_medication": "近期用药",
    "red_flag_notes": "风险提示",
}

_ACTION_CHECKLIST_LABELS = {
    "observe": "观察事项",
    "exams": "建议检查",
    "when_to_seek_care": "何时就医",
    "lifestyle": "生活方式建议",
}


def _conversation_rel_label(rel_type: str) -> str:
    normalized = str(rel_type or "")
    return _KG_REL_LABEL_MAP.get(normalized, normalized)


def _conversation_target_category(labels: Any) -> str:
    for label in labels or []:
        if label in _KG_TARGET_CATEGORY_MAP:
            return _KG_TARGET_CATEGORY_MAP[label]
    return "other"


def _conversation_group_key(rel_type: str, target_category: str) -> str:
    relation = str(rel_type or "")
    if relation in {"has_symptom", "相关症状", "临床表现"}:
        return "symptom"
    if relation in {"need_check", "检查"}:
        return "exam"
    if relation in {"common_drug", "recommand_drug", "drugs_of"}:
        return "drug"
    if relation in {"do_eat", "recommand_eat"}:
        return "food_recommended"
    if relation == "no_eat":
        return "food_avoid"
    if relation == "belongs_to":
        return "department"
    if relation in {"acompany_with", "并发症"}:
        return "complication"
    if relation == "治疗":
        return "treatment"
    if target_category == "drug":
        return "drug"
    if target_category == "exam":
        return "exam"
    if target_category == "department":
        return "department"
    if target_category == "symptom":
        return "symptom"
    if target_category == "treatment":
        return "treatment"
    return "other"


def _conversation_build_kg_context(raw_kg_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    metadata = _conversation_normalize_metadata(raw_kg_context)
    summary = str(metadata.get("summary") or "").strip()
    knowledge = metadata.get("knowledge")
    if not isinstance(knowledge, list):
        if not summary:
            return None
        return {"summary": summary, "groups": []}

    grouped: Dict[str, Dict[str, Any]] = {}
    seen = set()
    for triple in knowledge:
        if not isinstance(triple, dict):
            continue
        source = str(triple.get("source") or "").strip()
        relation = str(triple.get("relation") or "").strip()
        target = str(triple.get("target") or "").strip()
        if not source or not relation or not target:
            continue

        target_category = _conversation_target_category(
            triple.get("target_labels") or triple.get("source_labels")
        )
        item_key = (source, relation, target, target_category)
        if item_key in seen:
            continue
        seen.add(item_key)

        group_key = _conversation_group_key(relation, target_category)
        grouped.setdefault(
            group_key,
            {
                "key": group_key,
                "title": _KG_GROUP_TITLES[group_key],
                "category": group_key,
                "items": [],
            },
        )
        grouped[group_key]["items"].append(
            {
                "source": source,
                "relation": relation,
                "relation_label": _conversation_rel_label(relation),
                "target": target,
                "target_category": target_category,
            }
        )

    groups = [grouped[key] for key in _KG_GROUP_ORDER if key in grouped and grouped[key]["items"]]
    if not summary and not groups:
        return None
    return {"summary": summary, "groups": groups}


_CMEKG_FIELD_TO_GROUP = {
    "name": "disease",
    "symptom": "symptom",
    "check": "exam",
    "common_drug": "drug",
    "recommand_drug": "drug",
    "drug_detail": "drug",
    "do_eat": "food_recommended",
    "recommand_eat": "food_recommended",
    "not_eat": "food_avoid",
    "no_eat": "food_avoid",
    "cure_department": "department",
    "acompany": "complication",
    "cure_way": "treatment",
}

_CMEKG_GROUP_TITLES = {
    "symptom": "鐥囩姸涓庝綋寰?",
    "disease": "鐩稿叧鐤剧梾",
    "exam": "妫€鏌ヤ笌鍖栭獙",
    "drug": "鑽墿鐩稿叧",
    "food_recommended": "瀹滃悆涓庢帹鑽愰ギ椋?",
    "food_avoid": "楗绂佸繉",
    "department": "鐩稿叧绉戝",
    "complication": "浼撮殢闂",
    "treatment": "娌荤枟寤鸿",
    "other": "鍏朵粬鍏宠仈鐭ヨ瘑",
}

_CMEKG_GROUP_ORDER = [
    "symptom",
    "disease",
    "exam",
    "drug",
    "food_recommended",
    "food_avoid",
    "department",
    "complication",
    "treatment",
    "other",
]

_CMEKG_CATEGORY_TO_GROUP = {
    "symptom": "symptom",
    "disease": "disease",
    "exam": "exam",
    "drug": "drug",
    "department": "department",
    "treatment": "treatment",
    "food": "food_recommended",
}

_CMEKG_REL_TO_GROUP = {
    "check": "exam",
    "need_check": "exam",
    "common_drug": "drug",
    "recommand_drug": "drug",
    "drugs_of": "drug",
    "do_eat": "food_recommended",
    "recommand_eat": "food_recommended",
    "not_eat": "food_avoid",
    "no_eat": "food_avoid",
    "belongs_to": "department",
    "cure_department": "department",
    "acompany": "complication",
    "acompany_with": "complication",
    "cure_way": "treatment",
    "treatment": "treatment",
    "娌荤枟": "treatment",
    "妫€鏌?": "exam",
    "骞跺彂鐥?": "complication",
    "鐩稿叧鐥囩姸": "symptom",
    "涓村簥琛ㄧ幇": "symptom",
}

_CMEKG_ENTITY_GROUPS: Optional[Dict[str, Set[str]]] = None


def _cmekg_collect_values(value: Any) -> List[str]:
    if isinstance(value, str):
        text = value.strip()
        return [text] if text else []
    if isinstance(value, list):
        values = []
        for item in value:
            values.extend(_cmekg_collect_values(item))
        return values
    return []


def _cmekg_entity_groups() -> Dict[str, Set[str]]:
    global _CMEKG_ENTITY_GROUPS
    if _CMEKG_ENTITY_GROUPS is not None:
        return _CMEKG_ENTITY_GROUPS

    groups: Dict[str, Set[str]] = {key: set() for key in _CMEKG_GROUP_ORDER}
    data_path = Path(__file__).resolve().parents[2] / "data" / "medical.json"
    try:
        with data_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                for field, group_key in _CMEKG_FIELD_TO_GROUP.items():
                    for entity in _cmekg_collect_values(row.get(field)):
                        groups.setdefault(group_key, set()).add(entity)
    except OSError as exc:
        logger.warning(f"CMEKG dictionary load failed: {exc}")

    _CMEKG_ENTITY_GROUPS = groups
    return groups


def _cmekg_group_key(relation: str, target_category: str, target: str) -> str:
    target_text = str(target or "").strip()
    if target_text:
        for group_key in _CMEKG_GROUP_ORDER:
            if target_text in _cmekg_entity_groups().get(group_key, set()):
                return group_key

    category_key = _CMEKG_CATEGORY_TO_GROUP.get(str(target_category or ""))
    if category_key:
        return category_key

    relation_key = _CMEKG_REL_TO_GROUP.get(str(relation or "").strip())
    if relation_key:
        return relation_key

    if str(relation or "").strip() == "has_symptom":
        return "symptom"
    return "other"


def _cmekg_summary(groups: List[Dict[str, Any]], fallback_summary: str) -> str:
    if not groups:
        return fallback_summary
    first_source = ""
    labels = []
    for group in groups:
        if group.get("items") and not first_source:
            first_source = str(group["items"][0].get("source") or "")
        if group.get("items"):
            labels.append(_CMEKG_GROUP_TITLES.get(group["key"], group["key"]))
    if not labels:
        return fallback_summary
    source_text = first_source or "current symptom"
    label_text = ", ".join(labels[:6])
    return f"Relevant clinical knowledge for {source_text}: {label_text}."

def _conversation_build_cmekg_context(raw_kg_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    metadata = _conversation_normalize_metadata(raw_kg_context)
    fallback_summary = str(metadata.get("summary") or "").strip()
    knowledge = metadata.get("knowledge")
    if not isinstance(knowledge, list):
        if not fallback_summary:
            return None
        return {"summary": fallback_summary, "groups": []}

    grouped: Dict[str, Dict[str, Any]] = {}
    seen = set()
    for triple in knowledge:
        if not isinstance(triple, dict):
            continue
        source = str(triple.get("source") or "").strip()
        relation = str(triple.get("relation") or "").strip()
        target = str(triple.get("target") or "").strip()
        if not source or not relation or not target:
            continue

        target_category = _conversation_target_category(
            triple.get("target_labels") or triple.get("source_labels")
        )
        group_key = _cmekg_group_key(relation, target_category, target)
        item_key = (source, relation, target, group_key)
        if item_key in seen:
            continue
        seen.add(item_key)

        grouped.setdefault(
            group_key,
            {
                "key": group_key,
                "title": _CMEKG_GROUP_TITLES[group_key],
                "category": group_key,
                "items": [],
            },
        )
        grouped[group_key]["items"].append(
            {
                "source": source,
                "relation": relation,
                "relation_label": _conversation_rel_label(relation),
                "target": target,
                "target_category": group_key,
            }
        )

    groups = [grouped[key] for key in _CMEKG_GROUP_ORDER if key in grouped and grouped[key]["items"]]
    if not groups and not fallback_summary:
        return None
    return {"summary": _cmekg_summary(groups, fallback_summary), "groups": groups}


def _conversation_list_report_messages(conversation_id: int, db: Session) -> List[Message]:
    report_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.message_type == MessageType.FILE,
        )
        .order_by(desc(Message.created_at), desc(Message.id))
        .all()
    )
    return [
        message
        for message in report_messages
        if getattr(message, "message_type", None) in {MessageType.FILE, "file"}
    ][:3]


def _conversation_build_linked_reports(
    conversation_id: int,
    diagnosis_metadata: Optional[Dict[str, Any]],
    db: Session,
) -> List[Dict[str, Any]]:
    linked_reports: List[Dict[str, Any]] = []
    raw_linked_reports = (diagnosis_metadata or {}).get("linked_reports")
    if isinstance(raw_linked_reports, list):
        linked_reports = [
            {
                "message_id": item.get("message_id"),
                "file_name": item.get("file_name"),
                "file_type": item.get("file_type"),
                "report_type": item.get("report_type"),
                "ocr_text": item.get("ocr_text") or "",
            }
            for item in raw_linked_reports
            if isinstance(item, dict)
        ]
    if linked_reports:
        return linked_reports
    return [
        _conversation_serialize_report(message)
        for message in _conversation_list_report_messages(conversation_id, db)
    ]


def _conversation_format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "、".join(str(item) for item in value if item not in (None, ""))
    if isinstance(value, dict):
        return "；".join(
            f"{key}: {_conversation_format_value(item)}"
            for key, item in value.items()
            if item not in (None, "", [], {})
        )
    return str(value).strip()


def _conversation_summarize_structured_intake(structured_intake: Dict[str, Any]) -> str:
    lines = []
    for key, value in structured_intake.items():
        formatted = _conversation_format_value(value)
        if not formatted:
            continue
        label = _STRUCTURED_INTAKE_LABELS.get(key, key)
        lines.append(f"{label}: {formatted}")
    return "\n".join(lines)


def _conversation_summarize_reports(linked_reports: List[Dict[str, Any]]) -> str:
    lines = []
    for report in linked_reports[:3]:
        name = report.get("file_name") or report.get("report_type") or "报告"
        report_type = report.get("report_type") or report.get("file_type") or "检查报告"
        ocr_text = str(report.get("ocr_text") or "").strip()
        snippet = ocr_text[:120] + ("..." if len(ocr_text) > 120 else "")
        if snippet:
            lines.append(f"{name}（{report_type}）: {snippet}")
        else:
            lines.append(f"{name}（{report_type}）")
    return "\n".join(lines)


def _conversation_summarize_action_checklist(action_checklist: Optional[Dict[str, Any]]) -> str:
    checklist = action_checklist if isinstance(action_checklist, dict) else {}
    sections = []
    for key, label in _ACTION_CHECKLIST_LABELS.items():
        items = checklist.get(key)
        if not isinstance(items, list) or not items:
            continue
        sections.append(f"{label}: {'；'.join(str(item) for item in items if item)}")
    return "\n".join(sections)


def _conversation_create_record_title(conversation: Conversation, patient_name: Optional[str]) -> str:
    subject = conversation.chief_complaint or conversation.title or "诊疗记录"
    if patient_name:
        return f"{patient_name} - {subject}"[:200]
    return subject[:200]


def _conversation_get_diagnosis_context(conversation_id: int, db: Session) -> Dict[str, Any]:
    conversation = ConversationService.get_conversation_by_id(conversation_id, db)
    if not conversation:
        raise NotFoundException(f"会话 ID {conversation_id} 不存在")

    patient = db.query(User).filter(User.id == conversation.patient_id).first()
    conversation_metadata = _conversation_normalize_metadata(conversation)
    health_profile = patient.health_profile if patient and isinstance(patient.health_profile, dict) else {}
    patient_name = (patient.full_name or patient.username) if patient else None
    patient_gender = health_profile.get("gender")
    patient_age = calculate_age_from_birth_date(health_profile.get("birth_date"))

    assistant_messages = (
        db.query(Message)
        .filter(
            Message.conversation_id == conversation_id,
            Message.role == MessageRole.ASSISTANT,
        )
        .order_by(desc(Message.created_at), desc(Message.id))
        .all()
    )
    latest_diagnosis_message = _conversation_select_latest_diagnosis_message(assistant_messages)

    latest_diagnosis = None
    triage = conversation_metadata.get("triage")
    diagnosis_metadata: Dict[str, Any] = {}
    if latest_diagnosis_message:
        diagnosis_metadata = _conversation_normalize_metadata(latest_diagnosis_message)
        triage = triage or diagnosis_metadata.get("triage")
        latest_diagnosis = {
            "message_id": latest_diagnosis_message.id,
            "content": latest_diagnosis_message.content,
            "difficulty": diagnosis_metadata.get("difficulty"),
            "agents_used": diagnosis_metadata.get("agents_used"),
            "red_flags": diagnosis_metadata.get("red_flags") or [],
            "action_checklist": diagnosis_metadata.get("action_checklist"),
            "kg_context": _conversation_build_kg_context(diagnosis_metadata.get("kg_context")),
            "triage": diagnosis_metadata.get("triage"),
            "team_recruitment": diagnosis_metadata.get("team_recruitment"),
            "expert_opinions": diagnosis_metadata.get("expert_opinions") or [],
            "mdt_plan": diagnosis_metadata.get("mdt_plan"),
            "team_reports": diagnosis_metadata.get("team_reports") or [],
            "created_at": latest_diagnosis_message.created_at,
        }

    linked_reports = _conversation_build_linked_reports(conversation_id, diagnosis_metadata, db)
    medical_records = (
        db.query(MedicalRecord)
        .filter(MedicalRecord.conversation_id == conversation_id)
        .order_by(desc(MedicalRecord.updated_at), desc(MedicalRecord.id))
        .all()
    )

    return {
        "conversation": {
            "id": conversation.id,
            "title": conversation.title,
            "status": conversation.status.value if conversation.status else None,
            "chief_complaint": conversation.chief_complaint,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        },
        "patient": {
            "id": conversation.patient_id,
            "name": patient_name,
            "gender": patient_gender,
            "age": patient_age,
        },
        "health_profile": health_profile,
        "structured_intake": conversation_metadata.get("structured_intake") or {},
        "triage": triage,
        "linked_reports": linked_reports,
        "latest_diagnosis": latest_diagnosis,
        "medical_records": [
            {
                "id": record.id,
                "title": record.title,
                "status": record.status.value if record.status else None,
                "updated_at": record.updated_at,
            }
            for record in medical_records
        ],
    }


def _conversation_get_medical_record_draft(conversation_id: int, db: Session) -> Dict[str, Any]:
    conversation = ConversationService.get_conversation_by_id(conversation_id, db)
    if not conversation:
        raise NotFoundException(f"会话 ID {conversation_id} 不存在")

    context = _conversation_get_diagnosis_context(conversation_id, db)
    structured_intake = context.get("structured_intake") or {}
    linked_reports = context.get("linked_reports") or []
    latest_diagnosis = context.get("latest_diagnosis") or {}
    action_checklist = latest_diagnosis.get("action_checklist") or {}

    preliminary_diagnosis = str(latest_diagnosis.get("content") or "").strip()
    diagnosis_items = []
    if preliminary_diagnosis:
        diagnosis_items.append({"name": preliminary_diagnosis[:255], "type": "primary"})

    advice_summary = _conversation_summarize_action_checklist(action_checklist)
    return {
        "patient": context["patient"],
        "conversation": context["conversation"],
        "draft_record": {
            "title": _conversation_create_record_title(conversation, context["patient"].get("name")),
            "status": "draft",
            "chief_complaint": context["conversation"].get("chief_complaint"),
            "present_illness": _conversation_summarize_structured_intake(structured_intake)
            or context["conversation"].get("chief_complaint"),
            "past_history": _conversation_format_value(context.get("health_profile", {}).get("past_history")),
            "physical_examination": None,
            "auxiliary_examination": _conversation_summarize_reports(linked_reports),
            "preliminary_diagnosis": preliminary_diagnosis,
            "diagnosis": diagnosis_items,
            "treatment_plan": advice_summary,
            "medications": [],
            "medical_advice": advice_summary,
            "follow_up": _conversation_format_value(action_checklist.get("when_to_seek_care")),
            "metadata": {
                "source": "ai_draft",
                "source_conversation_id": conversation_id,
                "triage": context.get("triage"),
                "kg_context": latest_diagnosis.get("kg_context"),
            },
        },
    }


ConversationService.get_diagnosis_context = staticmethod(_conversation_get_diagnosis_context)
ConversationService.get_medical_record_draft = staticmethod(_conversation_get_medical_record_draft)
_conversation_build_kg_context = _conversation_build_cmekg_context


def _cmekg_summary(groups: List[Dict[str, Any]], fallback_summary: str) -> str:
    if not groups:
        return fallback_summary
    first_source = ""
    labels = []
    for group in groups:
        if group.get("items") and not first_source:
            first_source = str(group["items"][0].get("source") or "")
        if group.get("items"):
            labels.append(_CMEKG_GROUP_TITLES.get(group["key"], group["key"]))
    if not labels:
        return fallback_summary
    source_text = first_source or "current symptom"
    label_text = ", ".join(labels[:6])
    return f"Relevant clinical knowledge for {source_text}: {label_text}."


def _conversation_build_kg_context(raw_kg_context: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    return _conversation_build_cmekg_context(raw_kg_context)

