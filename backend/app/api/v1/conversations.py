"""
会话相关API
提供会话的创建、查询、更新等功能
"""
from datetime import datetime
from typing import Any, Dict, Optional, TypeVar, Type
from enum import Enum
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.dependencies import get_db
from app.services.conversation_service import ConversationService
from app.schemas.conversation import (
    ConversationCreate,
    ConversationUpdate,
    ConversationResponse,
    ConversationListResponse,
    ConversationStatusUpdate,
    ConversationComplexityUpdate,
    DiagnosisContextResponse,
    MedicalRecordDraftResponse,
)
from app.core.permissions import get_current_user, require_role, Role
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    BusinessException,
    AuthorizationException,
    to_http_exception,
)
from app.models.conversation import ConversationStatus, ComplexityLevel, CollaborationMode
from app.models.message import Message
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/conversations", tags=["会话"])

# 分页默认与上限：单次请求不宜过大，避免慢请求与内存峰值
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

_E = TypeVar("_E", bound=Enum)


def _parse_enum(value: Optional[str], enum_cls: Type[_E], param_name: str) -> Optional[_E]:
    """将查询参数字符串解析为枚举，无效时抛出 ValidationException。"""
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        raise ValidationException(f"无效的{param_name}: {value}")


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建新会话
    
    Args:
        conversation_data: 会话创建数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        创建的会话信息
    
    Raises:
        404: 患者或医生不存在
        403: 只有患者可以创建会话
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        # 患者、医生：不允许代他人创建会话，强制使用当前用户作为 patient_id
        if user_role == Role.PATIENT.value or user_role == Role.DOCTOR.value:
            if conversation_data.patient_id is not None and conversation_data.patient_id != user_id:
                raise AuthorizationException("无权代其他用户创建会话")
            conversation_data.patient_id = user_id
        elif user_role == Role.ADMIN.value:
            # 管理员可代建：仅当未传 patient_id 时用当前用户填充
            if conversation_data.patient_id is None:
                conversation_data.patient_id = user_id
        else:
            if conversation_data.patient_id is None:
                conversation_data.patient_id = user_id

        conversation = ConversationService.create_conversation(conversation_data, db)
        return ConversationResponse.model_validate(conversation)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"创建会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建会话失败"
        )


@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: Optional[int] = Query(None, ge=1, description="页码（与 page_size 配合使用）"),
    page_size: Optional[int] = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"每页条数（默认 {DEFAULT_PAGE_SIZE}，最大 {MAX_PAGE_SIZE}）",
    ),
    skip: int = Query(0, ge=0, description="跳过的记录数（与 limit 配合使用）"),
    limit: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description=f"返回的记录数（默认 {DEFAULT_PAGE_SIZE}，最大 {MAX_PAGE_SIZE}）",
    ),
    include_total: bool = Query(
        False,
        description="是否返回总条数（为 true 时会执行 count 查询，数据量大时可能较慢）",
    ),
    status_filter: Optional[str] = Query(None, description="会话状态过滤", alias="status"),
    complexity_level: Optional[str] = Query(None, description="复杂度级别过滤"),
    collaboration_mode: Optional[str] = Query(None, description="协作模式过滤"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取会话列表

    支持两种分页方式：
    - page/page_size：页码分页（推荐，前端友好）
    - skip/limit：偏移分页（兼容旧接口）

    page/page_size 优先级高于 skip/limit。

    仅传 page_size 时的语义：只改变每页条数，页码视为第 1 页（skip=0），
    即返回前 page_size 条记录。

    分页与性能说明：
    - 每页条数默认 20，最大 100，避免单次请求数据量过大导致慢请求与内存峰值。
    - 默认不返回总条数（total 为 null），仅返回本页数据与 has_next，以提升性能。
    - 若需总条数（如展示「共 N 条」），可传 include_total=true（数据量大时 count 可能较慢）。
    """
    # 统一转换为 skip/limit（仅传 page_size 时：第 1 页，条数=page_size）
    if page is not None and page_size is not None:
        skip = (page - 1) * page_size
        limit = page_size
    elif page_size is not None:
        skip = 0  # 仅改每页条数，页码仍为 1
        limit = page_size

    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        # 根据角色过滤
        patient_id = None
        doctor_id = None
        
        if user_role == Role.PATIENT.value:
            patient_id = user_id
        elif user_role == Role.DOCTOR.value:
            doctor_id = user_id
        
        # 解析枚举值
        status_enum = _parse_enum(status_filter, ConversationStatus, "会话状态")
        complexity_enum = _parse_enum(complexity_level, ComplexityLevel, "复杂度级别")
        collaboration_enum = _parse_enum(collaboration_mode, CollaborationMode, "协作模式")
        
        conversations, total, has_next = ConversationService.list_conversations(
            skip=skip,
            limit=limit,
            patient_id=patient_id,
            doctor_id=doctor_id,
            status=status_enum,
            complexity_level=complexity_enum,
            collaboration_mode=collaboration_enum,
            include_total=include_total,
            db=db,
        )
        
        return ConversationListResponse(
            total=total,
            items=[ConversationResponse.model_validate(c) for c in conversations],
            has_next=has_next,
        )
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取会话列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话列表失败"
        )


@router.get("/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取会话详情
    
    Args:
        conversation_id: 会话ID
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        会话详细信息
    
    Raises:
        404: 会话不存在
        403: 无权访问该会话
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 权限检查：患者只能查看自己的会话，医生可以查看分配给自己的会话
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权访问该会话")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id and conversation.doctor_id is not None:
                raise AuthorizationException("无权访问该会话")
        
        return ConversationResponse.model_validate(conversation)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取会话详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话详情失败"
        )


@router.get("/{conversation_id}/diagnosis-context", response_model=DiagnosisContextResponse)
async def get_diagnosis_context(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    """获取医生端诊断总览上下文。"""
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"浼氳瘽 ID {conversation_id} 涓嶅瓨鍦?")

        if user_role == Role.DOCTOR.value and conversation.doctor_id != user_id:
            raise AuthorizationException("鏃犳潈璁块棶璇ヤ細璇婅瘖鏂笂涓嬫枃")

        context = ConversationService.get_diagnosis_context(conversation_id, db)
        return DiagnosisContextResponse.model_validate(context)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"鑾峰彇璇婃柇涓婁笅鏂囧け璐? {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="鑾峰彇璇婃柇涓婁笅鏂囧け璐?"
        )
@router.get("/{conversation_id}/medical-record-draft", response_model=MedicalRecordDraftResponse)
async def get_medical_record_draft(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    """基于会话上下文返回病历草稿预填数据。"""
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")

        if user_role == Role.DOCTOR.value and conversation.doctor_id != user_id:
            raise AuthorizationException("无权查看该会话的病历草稿上下文")

        draft = ConversationService.get_medical_record_draft(conversation_id, db)
        return MedicalRecordDraftResponse.model_validate(draft)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取病历草稿失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取病历草稿失败"
        )


@router.post("/{conversation_id}/agent-feedback")
async def submit_conversation_agent_feedback(
    conversation_id: int,
    feedback: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        if user_role == Role.DOCTOR.value and conversation.doctor_id != user_id:
            raise AuthorizationException("无权反馈该会话的 Agent 结果")

        feedback_type = str(feedback.get("feedback_type") or "").strip()
        if feedback_type not in {"useful", "inaccurate", "missed_risk"}:
            raise ValidationException("Invalid feedback_type")

        message_id = feedback.get("message_id")
        entry = {
            "feedback_type": feedback_type,
            "comment": str(feedback.get("comment") or "").strip(),
            "doctor_id": user_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "feedback_source": "doctor_review",
            "created_at": datetime.utcnow().isoformat(),
        }

        metadata = dict(conversation.extra_metadata or {})
        feedback_items = list(metadata.get("agent_feedback") or [])
        feedback_items.append(entry)
        metadata["agent_feedback"] = feedback_items
        metadata["feedback_source"] = "doctor_review"
        conversation.extra_metadata = metadata

        if message_id:
            message = db.query(Message).filter(
                Message.id == message_id,
                Message.conversation_id == conversation_id,
            ).first()
            if message:
                message_metadata = dict(message.extra_metadata or {})
                message_feedback = list(message_metadata.get("agent_feedback") or [])
                message_feedback.append(entry)
                message_metadata["agent_feedback"] = message_feedback
                message_metadata["feedback_source"] = "doctor_review"
                message.extra_metadata = message_metadata

        db.commit()
        return {"saved": True, "feedback": entry}
    except (NotFoundException, ValidationException, AuthorizationException) as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"保存 Agent 反馈失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存 Agent 反馈失败",
        )


@router.put("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    conversation_data: ConversationUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新会话信息
    
    Args:
        conversation_id: 会话ID
        conversation_data: 会话更新数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的会话信息
    
    Raises:
        404: 会话不存在
        403: 无权修改该会话
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 权限检查：只有患者或医生可以更新会话
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权修改该会话")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id:
                raise AuthorizationException("无权修改该会话")
        
        conversation = ConversationService.update_conversation(
            conversation_id, conversation_data, db
        )
        return ConversationResponse.model_validate(conversation)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"更新会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新会话失败"
        )


@router.patch("/{conversation_id}/status", response_model=ConversationResponse)
async def update_conversation_status(
    conversation_id: int,
    status_data: ConversationStatusUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新会话状态
    
    权限：患者仅能改自己的会话，医生仅能改已分配给自己的会话，管理员可改全部。
    
    Args:
        conversation_id: 会话ID
        status_data: 状态更新数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的会话信息
    
    Raises:
        404: 会话不存在
        400: 无效的状态值
        403: 无权修改该会话状态
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")

        # 会话级权限：患者仅能改自己的，医生仅能改已分配给自己的，管理员可改全部
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权修改该会话状态")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id:
                raise AuthorizationException("无权修改该会话状态")
        # ADMIN 无需额外校验，可修改任意会话

        conversation = ConversationService.update_conversation_status(
            conversation_id, status_data, db
        )
        return ConversationResponse.model_validate(conversation)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"更新会话状态失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新会话状态失败"
        )


@router.patch("/{conversation_id}/complexity", response_model=ConversationResponse)
async def update_conversation_complexity(
    conversation_id: int,
    complexity_data: ConversationComplexityUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新会话复杂度评估结果
    
    通常由智能体系统调用，用于记录复杂度评估和协作模式。
    接口对已登录用户开放，权限与更新会话一致：患者仅能改自己的会话，
    医生仅能改已分配给自己的会话，管理员可改全部。
    
    Args:
        conversation_id: 会话ID
        complexity_data: 复杂度更新数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的会话信息
    
    Raises:
        404: 会话不存在
        400: 无效的枚举值
        403: 无权修改该会话
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")

        # 与 update_conversation 一致的会话级权限校验
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权修改该会话")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id:
                raise AuthorizationException("无权修改该会话")
        # ADMIN 可修改任意会话

        conversation = ConversationService.update_complexity(
            conversation_id, complexity_data, db
        )
        return ConversationResponse.model_validate(conversation)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"更新会话复杂度失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新会话复杂度失败"
        )


@router.post("/{conversation_id}/assign-doctor", response_model=ConversationResponse)
async def assign_doctor(
    conversation_id: int,
    doctor_id: int,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    """
    分配医生到会话
    
    只有医生或管理员可以分配医生
    
    Args:
        conversation_id: 会话ID
        doctor_id: 医生ID
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的会话信息
    
    Raises:
        404: 会话或医生不存在
        400: 会话已有医生、状态不允许分配或指定用户非医生账号
    """
    try:
        conversation = ConversationService.assign_doctor(
            conversation_id, doctor_id, db
        )
        return ConversationResponse.model_validate(conversation)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"分配医生失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="分配医生失败"
        )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除会话
    
    Args:
        conversation_id: 会话ID
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        204 No Content
    
    Raises:
        404: 会话不存在
        403: 无权删除该会话
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 权限检查：只有患者或管理员可以删除会话；医生无权删除任意会话
        if user_role == Role.DOCTOR.value:
            raise AuthorizationException("无权删除该会话")
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权删除该会话")
        # 管理员可删除任意会话，无需校验会话归属

        ConversationService.delete_conversation(conversation_id, db)
        return None
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except BusinessException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"删除会话失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除会话失败"
        )


# 导出
__all__ = ["router"]
