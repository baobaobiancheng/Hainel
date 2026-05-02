"""
消息相关API
提供消息的发送、查询、更新等功能
"""
from mimetypes import guess_type
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
import asyncio

from app.dependencies import get_db
from app.services.message_service import MessageService
from app.services.conversation_service import ConversationService
from app.schemas.message import (
    MessageCreate,
    MessageUpdate,
    MessageResponse,
    MessageListResponse,
    MessageReadUpdate,
)
from app.schemas.conversation import ConversationStatusUpdate
from app.core.permissions import get_current_user, Role
from app.core.exceptions import (
    NotFoundException,
    ValidationException,
    AuthorizationException,
    to_http_exception,
)
from app.models.message import MessageRole, MessageType
from app.models.message import Message
from app.models.user import User
from app.utils.file_handler import file_handler, FileHandlerError
from app.utils.logger import get_logger
# from app.agents.orchestrator.orchestrator import AgentOrchestrator
# from app.agents.base.agent_interface import AgentContext
from app.services.consultation_service import consultation_service
from app.services.doctor_service import DoctorService
from app.services.triage_service import TriageResult, triage_service
from app.agents.evaluation.policy_registry import PolicyRegistry
from app.api.v1.long_polling import send_message_notification
from app.api.v1.websocket import push_to_doctor

logger = get_logger(__name__)

router = APIRouter(prefix="/messages", tags=["消息"])

_ocr_service = None


def get_ocr_service():
    """获取症状图片 OCR 服务实例（DashScope qwen-vl-plus）。"""
    global _ocr_service
    if _ocr_service is None:
        from app.ai.ocr.dashscope_ocr import DashScopeOCRService
        _ocr_service = DashScopeOCRService()
    return _ocr_service


@router.post("/image", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image_message(
    conversation_id: int = Form(..., description="会话ID"),
    file: UploadFile = File(..., description="症状图片"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """上传症状图片并保存为会话中的图片消息。"""
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")

        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权在该会话中上传图片")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id and conversation.doctor_id is not None:
                raise AuthorizationException("无权在该会话中上传图片")

        ext = (file.filename or "").rsplit(".", 1)[-1].lower()
        if ext not in {"jpg", "jpeg", "png", "webp", "bmp"}:
            raise ValidationException("症状图片仅支持 jpg、jpeg、png、webp、bmp 格式")

        try:
            filename = await file_handler.save_upload_file(
                file, subdir=f"messages/{conversation_id}"
            )
            file_size = file_handler.get_file_size(filename, subdir=f"messages/{conversation_id}")
        except FileHandlerError as e:
            raise ValidationException(f"图片保存失败: {e}")

        ocr_text = ""
        ocr_metadata = None
        try:
            file_content = await file_handler.read_file(filename, subdir=f"messages/{conversation_id}")
            ocr_result = await asyncio.wait_for(
                asyncio.to_thread(get_ocr_service().recognize_bytes, file_content),
                timeout=30.0,
            )
            ocr_text = ocr_result.text
            ocr_metadata = {
                "text": ocr_text,
                "confidence": ocr_result.confidence,
                "model": (ocr_result.metadata or {}).get("model"),
            }
        except asyncio.TimeoutError:
            logger.warning("症状图片 OCR 识别超时，跳过 OCR")
        except Exception as e:
            logger.warning(f"症状图片 OCR 识别失败，跳过 OCR: {e}")

        file_url = f"/api/v1/messages/images/{conversation_id}/{filename}"
        message = MessageService.create_message(
            MessageCreate(
                conversation_id=conversation_id,
                role="user",
                message_type="image",
                content="上传了一张症状图片",
                file_url=file_url,
                file_name=file.filename or filename,
                file_size=file_size,
                file_type=file.content_type or guess_type(filename)[0] or "image/*",
                metadata={
                    "source": "symptom_image",
                    "ocr_result": ocr_metadata,
                },
            ),
            user_id=user_id,
            db=db,
        )
        return MessageResponse.model_validate(message)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"上传图片消息失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="上传图片失败"
        )


@router.get("/images/{conversation_id}/{filename}")
async def get_image_message_file(conversation_id: int, filename: str):
    """读取聊天图片。文件名为 UUID，供小程序 image 组件直接展示。"""
    try:
        content = await file_handler.read_file(filename, subdir=f"messages/{conversation_id}")
    except FileHandlerError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"图片不存在: {e}")

    return Response(content=content, media_type=guess_type(filename)[0] or "image/jpeg")


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    message_data: MessageCreate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    创建新消息（发送消息）
    
    Args:
        message_data: 消息创建数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        创建的消息信息
    
    Raises:
        404: 会话不存在
        400: 无效的消息类型或角色
        403: 无权在该会话中发送消息
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        # 验证会话是否存在并检查权限
        conversation = ConversationService.get_conversation_by_id(
            message_data.conversation_id, db
        )
        if not conversation:
            raise NotFoundException(f"会话 ID {message_data.conversation_id} 不存在")
        
        # 权限检查：患者只能在自己的会话中发送消息
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权在该会话中发送消息")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id:
                raise AuthorizationException("无权在该会话中发送消息")
        
        # 设置用户ID（如果是用户消息，兼容前端传 "user" 或 "USER"）
        if message_data.role.strip().upper() == MessageRole.USER.value:
            user_id_for_message = user_id
        else:
            user_id_for_message = None
        
        message = MessageService.create_message(
            message_data, user_id=user_id_for_message, db=db
        )

        # 获取会话信息用于AI分析
        conversation = ConversationService.get_conversation_by_id(
            message_data.conversation_id, db
        )

        # 返回用户消息后，创建一条"智能分析中"的系统消息
        analyzing_message = MessageService.create_message(
            MessageCreate(
                conversation_id=message_data.conversation_id,
                role="system",
                message_type="text",
                content="正在智能分析您的问题，请稍候..."
            ),
            user_id=None,
            db=db
        )

        analysis_message = message_data.content
        metadata = message_data.metadata or {}
        symptom_image_ocr_text = metadata.get("symptom_image_ocr_text")
        if symptom_image_ocr_text:
            analysis_message = (
                f"{message_data.content}\n\n"
                f"【症状图片OCR识别结果，仅供辅助参考】\n{symptom_image_ocr_text}"
            )

        # 异步触发AI分析流程
        asyncio.create_task(_process_ai_analysis(
            conversation_id=message_data.conversation_id,
            patient_id=conversation.patient_id,
            user_message=analysis_message,
            analyzing_message_id=analyzing_message.id
        ))

        # 返回用户消息和分析中的系统消息
        return MessageResponse.model_validate(message)
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"创建消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建消息失败"
        )


@router.get("/conversation/{conversation_id}", response_model=MessageListResponse)
async def list_messages(
    conversation_id: int,
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的记录数"),
    role: Optional[str] = Query(None, description="消息角色过滤"),
    message_type: Optional[str] = Query(None, description="消息类型过滤"),
    agent_id: Optional[str] = Query(None, description="智能体ID过滤"),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取会话的消息列表
    
    Args:
        conversation_id: 会话ID
        skip: 跳过的记录数
        limit: 返回的记录数
        role: 消息角色过滤
        message_type: 消息类型过滤
        agent_id: 智能体ID过滤
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        消息列表和总数
    
    Raises:
        404: 会话不存在
        403: 无权访问该会话
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        # 验证会话是否存在并检查权限
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        # 权限检查
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权访问该会话")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id and conversation.doctor_id is not None:
                raise AuthorizationException("无权访问该会话")
        
        # 解析枚举值（兼容 "user"/"USER" 等，统一转为大写）
        role_enum = None
        if role:
            try:
                role_enum = MessageRole(role.strip().upper())
            except ValueError:
                raise ValidationException(f"无效的消息角色: {role}")
        
        message_type_enum = None
        if message_type:
            try:
                message_type_enum = MessageType(message_type)
            except ValueError:
                raise ValidationException(f"无效的消息类型: {message_type}")
        
        messages, total = MessageService.list_messages(
            conversation_id=conversation_id,
            skip=skip,
            limit=limit,
            role=role_enum,
            message_type=message_type_enum,
            agent_id=agent_id,
            db=db,
        )
        
        return MessageListResponse(
            total=total,
            items=[MessageResponse.model_validate(m) for m in messages],
        )
    except NotFoundException as e:
        raise to_http_exception(e)
    except ValidationException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取消息列表失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息列表失败"
        )


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取消息详情
    
    Args:
        message_id: 消息ID
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        消息详细信息
    
    Raises:
        404: 消息不存在
        403: 无权访问该消息
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        # 验证会话权限
        conversation = ConversationService.get_conversation_by_id(
            message.conversation_id, db
        )
        if not conversation:
            raise NotFoundException(f"会话 ID {message.conversation_id} 不存在")
        
        # 权限检查
        if user_role == Role.PATIENT.value:
            if conversation.patient_id != user_id:
                raise AuthorizationException("无权访问该消息")
        elif user_role == Role.DOCTOR.value:
            if conversation.doctor_id != user_id and conversation.doctor_id is not None:
                raise AuthorizationException("无权访问该消息")
        
        return MessageResponse.model_validate(message)
    except NotFoundException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取消息详情失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取消息详情失败"
        )


@router.put("/{message_id}", response_model=MessageResponse)
async def update_message(
    message_id: int,
    message_data: MessageUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    更新消息
    
    通常用于编辑消息内容或标记已读
    
    Args:
        message_id: 消息ID
        message_data: 消息更新数据
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的消息信息
    
    Raises:
        404: 消息不存在
        403: 无权修改该消息
    """
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")
        
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        # 权限检查：只有消息发送者可以编辑消息
        if message.user_id != user_id:
            raise AuthorizationException("无权修改该消息")
        
        message = MessageService.update_message(message_id, message_data, db)
        return MessageResponse.model_validate(message)
    except NotFoundException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"更新消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新消息失败"
        )


@router.post("/mark-read", response_model=List[MessageResponse])
async def mark_messages_as_read(
    read_data: MessageReadUpdate,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    批量标记消息为已读
    
    Args:
        read_data: 已读更新数据（包含消息ID列表）
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        更新后的消息列表
    """
    try:
        messages = MessageService.mark_messages_as_read(read_data, db)
        return [MessageResponse.model_validate(m) for m in messages]
    except Exception as e:
        logger.error(f"标记消息已读失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="标记消息已读失败"
        )


@router.get("/conversation/{conversation_id}/unread-count")
async def get_unread_count(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    获取会话的未读消息数量
    
    Args:
        conversation_id: 会话ID
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        未读消息数量
    """
    try:
        user_id = current_user.get("id")
        
        # 验证会话权限
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            raise NotFoundException(f"会话 ID {conversation_id} 不存在")
        
        count = MessageService.get_unread_count(
            conversation_id, user_id=user_id, db=db
        )
        return {"conversation_id": conversation_id, "unread_count": count}
    except NotFoundException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"获取未读消息数量失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取未读消息数量失败"
        )


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    message_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    删除消息
    
    Args:
        message_id: 消息ID
        current_user: 当前用户信息
        db: 数据库会话
    
    Returns:
        204 No Content
    
    Raises:
        404: 消息不存在
        403: 无权删除该消息
    """
    try:
        user_id = current_user.get("id")
        
        message = MessageService.get_message_by_id(message_id, db)
        if not message:
            raise NotFoundException(f"消息 ID {message_id} 不存在")
        
        # 权限检查：只有消息发送者可以删除消息
        if message.user_id != user_id:
            raise AuthorizationException("无权删除该消息")
        
        MessageService.delete_message(message_id, db)
        return None
    except NotFoundException as e:
        raise to_http_exception(e)
    except AuthorizationException as e:
        raise to_http_exception(e)
    except Exception as e:
        logger.error(f"删除消息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除消息失败"
        )


# 导出
__all__ = ["router"]


def _apply_triage_assignment(
    conversation,
    diagnosis_result: Dict[str, Any],
    user_message: str,
    health_profile: Optional[Dict[str, Any]],
    structured_intake: Optional[Dict[str, Any]],
    linked_reports: List[Dict[str, Any]],
    db: Session,
) -> tuple[TriageResult, Optional[User]]:
    """根据诊断结果进行科室分诊，并在需要时自动分配对应科室医生。"""
    triage_result = triage_service.triage(
        symptoms=user_message,
        medical_history=conversation.chief_complaint,
        health_profile=health_profile,
        structured_intake=structured_intake,
        linked_reports=linked_reports,
        diagnosis_result=diagnosis_result,
        kg_summary=(diagnosis_result.get("kg_context") or {}).get("summary"),
    )

    assigned_doctor = None
    if triage_result.requires_doctor:
        assigned_doctor = DoctorService.auto_assign_doctor(
            conversation.id,
            triage_result.department,
            db,
        )

    metadata = dict(conversation.extra_metadata or {})
    metadata["triage"] = triage_result.to_metadata()
    if assigned_doctor:
        metadata["assigned_doctor_id"] = assigned_doctor.id
    conversation.extra_metadata = metadata
    db.commit()

    return triage_result, assigned_doctor


async def _notify_assigned_doctor(
    assigned_doctor: Optional[User],
    conversation,
    triage_result: TriageResult,
) -> None:
    """向被分配医生定向推送新会话通知。"""
    if not assigned_doctor:
        logger.warning(
            f"会话 {conversation.id} 需要医生介入，但未分配到 {triage_result.department_name} 医生"
        )
        return

    await push_to_doctor(
        doctor_id=assigned_doctor.id,
        message_type="new_session",
        data={
            "conversation_id": conversation.id,
            "patient_id": conversation.patient_id,
            "chief_complaint": conversation.chief_complaint or "",
            "department": triage_result.department_name,
            "department_code": triage_result.department.value,
            "urgency": triage_result.urgency,
            "triage_reason": triage_result.reason,
            "triage_confidence": triage_result.confidence,
        },
    )


def _build_shadow_policy_trace(
    conversation,
    diagnosis_result: Dict[str, Any],
    triage_result: TriageResult,
    structured_intake: Optional[Dict[str, Any]],
    linked_reports: List[Dict[str, Any]],
) -> Dict[str, Any]:
    registry = PolicyRegistry()
    intake = structured_intake if isinstance(structured_intake, dict) else {}
    main_symptom = str(intake.get("main_symptom") or "")
    red_flag_count = len(diagnosis_result.get("red_flags") or [])

    route_state = {
        "chief_complaint": conversation.chief_complaint or "",
        "main_symptom": main_symptom,
        "red_flag_count": red_flag_count,
        "report_count": len(linked_reports),
    }
    triage_state = {
        "chief_complaint": conversation.chief_complaint or "",
        "main_symptom": main_symptom,
        "red_flag_count": red_flag_count,
        "requires_doctor": bool(triage_result.requires_doctor),
    }

    recommendations: Dict[str, Any] = {}
    routing_action = registry.recommend("routing", route_state)
    if routing_action:
        recommendations["routing"] = {
            "state_summary": route_state,
            "candidate_actions": [routing_action],
            "final_action": routing_action,
            "policy_version": (registry.get_active_policy("routing") or {}).get("version"),
        }

    triage_action = registry.recommend("triage", triage_state)
    if triage_action:
        recommendations["triage"] = {
            "state_summary": triage_state,
            "candidate_actions": [triage_action],
            "final_action": triage_action,
            "policy_version": (registry.get_active_policy("triage") or {}).get("version"),
        }

    if not recommendations:
        return {}
    return {"mode": "shadow", "recommendations": recommendations}


async def _process_ai_analysis(
    conversation_id: int,
    patient_id: int,
    user_message: str,
    analyzing_message_id: int
):
    """
    异步处理AI分析流程

    Args:
        conversation_id: 会话ID
        patient_id: 患者ID
        user_message: 用户发送的消息内容
        analyzing_message_id: "正在分析"消息的ID
    """
    from app.database.session import SessionLocal

    # 创建新的数据库会话
    db = SessionLocal()
    try:
        logger.info(f"开始AI分析流程：会话 {conversation_id}, 患者ID {patient_id}")

        # 获取会话信息
        conversation = ConversationService.get_conversation_by_id(conversation_id, db)
        if not conversation:
            logger.error(f"会话 {conversation_id} 不存在")
            return

        patient = db.query(User).filter(User.id == patient_id).first()
        health_profile = patient.health_profile if patient and patient.health_profile else None
        conversation_metadata = conversation.extra_metadata or {}
        structured_intake = conversation_metadata.get("structured_intake")
        report_messages = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.message_type == MessageType.FILE,
            )
            .order_by(Message.created_at.desc())
            .limit(3)
            .all()
        )
        linked_reports: List[Dict[str, Any]] = []
        for report in report_messages:
            report_metadata = report.extra_metadata or {}
            ocr_result = report_metadata.get("ocr_result") or {}
            linked_reports.append({
                "message_id": report.id,
                "file_name": report.file_name,
                "file_type": report_metadata.get("file_type") or report.file_type,
                "report_type": report_metadata.get("report_type"),
                "ocr_text": ocr_result.get("text") or "",
            })

        logger.info(f"[MDAgent] 开始诊断分析，用户消息: {user_message[:50]}...")

        # 使用 consultation_service 进行诊断
        diagnosis_result = consultation_service.diagnose(
            symptoms=user_message,
            medical_history=conversation.chief_complaint,
            health_profile=health_profile,
            structured_intake=structured_intake,
            linked_reports=linked_reports,
        )

        logger.info(f"[MDAgent] 诊断结果返回: {str(diagnosis_result)[:200]}...")

        response_text = diagnosis_result.get("diagnosis", "感谢您的咨询。")
        triage_result, assigned_doctor = _apply_triage_assignment(
            conversation=conversation,
            diagnosis_result=diagnosis_result,
            user_message=user_message,
            health_profile=health_profile,
            structured_intake=structured_intake,
            linked_reports=linked_reports,
            db=db,
        )
        policy_trace = _build_shadow_policy_trace(
            conversation=conversation,
            diagnosis_result=diagnosis_result,
            triage_result=triage_result,
            structured_intake=structured_intake,
            linked_reports=linked_reports,
        )

        logger.info(f"AI分析完成：会话 {conversation_id}")

        # 删除"正在分析"消息
        try:
            MessageService.delete_message(analyzing_message_id, db)
        except Exception as e:
            logger.warning(f"删除分析中消息失败: {e}")

        # 创建AI响应消息，传递诊断分析结果到 metadata
        metadata = {
            "difficulty": diagnosis_result.get("difficulty"),
            "agents_used": diagnosis_result.get("agents_used"),
            "analysis_type": "智能诊断",
            "red_flags": diagnosis_result.get("red_flags", []),
            "action_checklist": diagnosis_result.get("action_checklist"),
            "linked_reports": linked_reports,
            "structured_intake": structured_intake,
            "kg_context": diagnosis_result.get("kg_context"),
            "triage": triage_result.to_metadata(),
            "assigned_doctor_id": assigned_doctor.id if assigned_doctor else None,
        }
        # 团队招募信息（intermediate 级别）
        if diagnosis_result.get("team_recruitment"):
            metadata["team_recruitment"] = diagnosis_result.get("team_recruitment")
        if diagnosis_result.get("expert_opinions"):
            metadata["expert_opinions"] = diagnosis_result.get("expert_opinions")
        # 多学科团队方案（advanced 级别）
        if diagnosis_result.get("mdt_plan"):
            metadata["mdt_plan"] = diagnosis_result.get("mdt_plan")
        if diagnosis_result.get("team_reports"):
            metadata["team_reports"] = diagnosis_result.get("team_reports")
        if policy_trace:
            metadata["policy_trace"] = policy_trace

        ai_response = MessageService.create_message(
            MessageCreate(
                conversation_id=conversation_id,
                role="assistant",
                message_type="text",
                content=response_text,
                metadata=metadata,
            ),
            user_id=None,
            db=db
        )

        # 发送消息通知（通过轮询）
        await send_message_notification(ai_response.id, conversation_id, db)
        await _notify_assigned_doctor(assigned_doctor, conversation, triage_result)

        # 更新会话状态为ACTIVE
        ConversationService.update_conversation_status(
            conversation_id,
            ConversationStatusUpdate(status="active"),
            db
        )

        logger.info(f"AI响应消息已创建：会话 {conversation_id}, 消息ID {ai_response.id}")

    except Exception as e:
        logger.error(f"AI分析流程失败：会话 {conversation_id}, 错误: {e}", exc_info=True)

        # 更新分析中消息为错误提示
        try:
            from app.schemas.message import MessageUpdate
            MessageService.update_message(
                analyzing_message_id,
                MessageUpdate(content="抱歉，分析过程中出现错误，请稍后重试或联系医生。"),
                db
            )
        except Exception as update_error:
            logger.warning(f"更新错误消息失败: {update_error}")
    finally:
        db.close()
