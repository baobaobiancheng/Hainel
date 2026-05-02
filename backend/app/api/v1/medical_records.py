"""
Medical record API routes.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    AuthorizationException,
    BusinessException,
    NotFoundException,
    ValidationException,
    to_http_exception,
)
from app.core.permissions import Role, get_current_user, require_role
from app.dependencies import get_db
from app.models.medical_record import MedicalRecord, MedicalRecordStatus
from app.schemas.medical_record import (
    MedicalRecordCreate,
    MedicalRecordListResponse,
    MedicalRecordResponse,
    MedicalRecordReview,
    MedicalRecordStatusUpdate,
    MedicalRecordUpdate,
)
from app.services.medical_record_service import MedicalRecordService
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/medical-records", tags=["medical-records"])


def _serialize_medical_record(record: MedicalRecord) -> MedicalRecordResponse:
    patient = getattr(record, "patient", None)
    conversation = getattr(record, "conversation", None)
    patient_name = None
    if patient is not None:
        patient_name = getattr(patient, "full_name", None) or getattr(patient, "username", None)

    conversation_title = None
    if conversation is not None:
        conversation_title = getattr(conversation, "title", None) or getattr(conversation, "chief_complaint", None)

    return MedicalRecordResponse.model_validate(
        {
            "id": record.id,
            "patient_id": record.patient_id,
            "patient_name": patient_name,
            "conversation_id": record.conversation_id,
            "conversation_title": conversation_title,
            "reviewed_by": record.reviewed_by,
            "title": record.title,
            "chief_complaint": record.chief_complaint,
            "present_illness": record.present_illness,
            "past_history": record.past_history,
            "physical_examination": record.physical_examination,
            "auxiliary_examination": record.auxiliary_examination,
            "diagnosis": record.diagnosis,
            "treatment_plan": record.treatment_plan,
            "medications": record.medications,
            "medical_advice": record.medical_advice,
            "follow_up": record.follow_up,
            "status": record.status.value if isinstance(record.status, MedicalRecordStatus) else record.status,
            "content": record.content,
            "agent_name": record.agent_name,
            "agent_id": record.agent_id,
            "review_comment": record.review_comment,
            "reviewed_at": record.reviewed_at,
            "archived_at": record.archived_at,
            "metadata": record.extra_metadata or {},
            "created_at": record.created_at,
            "updated_at": record.updated_at,
        }
    )


def _serialize_medical_records(records: List[MedicalRecord]) -> List[MedicalRecordResponse]:
    return [_serialize_medical_record(record) for record in records]


def _doctor_can_view_record(record: MedicalRecord, doctor_id: Optional[int]) -> bool:
    status_value = record.status.value if isinstance(record.status, MedicalRecordStatus) else record.status

    if status_value in {
        MedicalRecordStatus.DRAFT.value,
        MedicalRecordStatus.CONFIRMED.value,
        MedicalRecordStatus.ARCHIVED.value,
    }:
        return True

    return record.reviewed_by == doctor_id


def _record_status_value(record: MedicalRecord) -> str:
    return record.status.value if isinstance(record.status, MedicalRecordStatus) else str(record.status)


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _medical_record_quality_check(record: MedicalRecord) -> Dict[str, Any]:
    metadata = record.extra_metadata if isinstance(record.extra_metadata, dict) else {}
    triage = metadata.get("triage") if isinstance(metadata.get("triage"), dict) else {}
    diagnosis_context = metadata.get("diagnosis_context") if isinstance(metadata.get("diagnosis_context"), dict) else {}
    red_flags = metadata.get("red_flags") or diagnosis_context.get("red_flags") or []
    linked_reports = metadata.get("linked_reports") or diagnosis_context.get("linked_reports") or []

    blocking: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    if not _normalize_text(record.chief_complaint):
        blocking.append("主诉缺失，不能确认正式病历。")
    if not _normalize_text(record.present_illness):
        warnings.append("现病史为空，建议补充症状起病时间、持续时间、诱因和伴随症状。")
    if not record.diagnosis:
        blocking.append("初步诊断为空，不能确认正式病历。")
    if not _normalize_text(record.treatment_plan) and not _normalize_text(record.medical_advice):
        warnings.append("处理方案和医嘱均为空，建议补充下一步处理建议。")
    if red_flags and not _normalize_text(record.medical_advice):
        blocking.append("存在红旗症状，但病历未记录医嘱或就医提醒。")
    if linked_reports and not _normalize_text(record.auxiliary_examination):
        warnings.append("会话有关联检查报告，但辅助检查摘要为空。")
    if triage.get("urgency") in {"high", "urgent"} and not _normalize_text(record.treatment_plan):
        warnings.append("分诊为高风险或紧急，但处理方案为空。")

    if _normalize_text(record.present_illness) and record.diagnosis and _normalize_text(record.medical_advice):
        suggestions.append("核心诊疗字段已填写，确认前请再次核对诊断和医嘱。")

    if blocking:
        level = "blocked"
        decision = "高风险阻止确认"
    elif warnings:
        level = "warning"
        decision = "建议补充后确认"
    else:
        level = "pass"
        decision = "可确认"

    return {
        "level": level,
        "decision": decision,
        "blocking": blocking,
        "warnings": warnings,
        "suggestions": suggestions,
        "checked_at": datetime.utcnow().isoformat(),
    }


def _build_assisted_record_fields(record: MedicalRecord) -> Dict[str, str]:
    metadata = record.extra_metadata if isinstance(record.extra_metadata, dict) else {}
    structured_intake = metadata.get("structured_intake") if isinstance(metadata.get("structured_intake"), dict) else {}
    action_checklist = metadata.get("action_checklist") if isinstance(metadata.get("action_checklist"), dict) else {}

    present_illness_parts = []
    for key in ("main_symptom", "symptom", "duration", "onset", "severity", "accompanying_symptoms"):
        value = structured_intake.get(key)
        if value:
            present_illness_parts.append(f"{key}: {value}")

    advice_parts = []
    for key in ("observe", "when_to_seek_care", "self_care", "follow_up"):
        value = action_checklist.get(key)
        if isinstance(value, list):
            advice_parts.extend(str(item) for item in value if item)
        elif value:
            advice_parts.append(str(value))

    result: Dict[str, str] = {}
    if not _normalize_text(record.present_illness) and present_illness_parts:
        result["present_illness"] = "\n".join(present_illness_parts)
    if not _normalize_text(record.treatment_plan):
        result["treatment_plan"] = "建议结合患者当前症状、检查报告和分诊风险完善处理方案。"
    if not _normalize_text(record.medical_advice) and advice_parts:
        result["medical_advice"] = "\n".join(advice_parts)
    if not _normalize_text(record.follow_up):
        result["follow_up"] = "建议按病情变化及时复诊；如症状加重或出现红旗症状，应立即线下就医。"
    return result


@router.post("", response_model=MedicalRecordResponse, status_code=status.HTTP_201_CREATED)
async def create_medical_record(
    record_data: MedicalRecordCreate,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        medical_record = MedicalRecordService.create_medical_record(record_data, db)
        return _serialize_medical_record(medical_record)
    except NotFoundException as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Create medical record failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建病历失败",
        )


@router.get("", response_model=MedicalRecordListResponse)
async def list_medical_records(
    page: Optional[int] = Query(None, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=1000),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    patient_id: Optional[int] = Query(None),
    conversation_id: Optional[int] = Query(None),
    status_value: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None, min_length=1),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if page is not None and page_size is not None:
        skip = (page - 1) * page_size
        limit = page_size
    elif page_size is not None:
        limit = page_size

    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        reviewed_by = None
        if user_role == Role.PATIENT.value:
            patient_id = user_id
        elif user_role == Role.DOCTOR.value and status_value == MedicalRecordStatus.REVIEWED.value:
            reviewed_by = user_id

        status_enum = None
        if status_value:
            try:
                status_enum = MedicalRecordStatus(status_value)
            except ValueError as exc:
                raise ValidationException(f"无效的病历状态: {status_value}") from exc

        keyword = (search or "").strip()
        if keyword:
            records, total = MedicalRecordService.search_medical_records(
                keyword=keyword,
                skip=skip,
                limit=limit,
                patient_id=patient_id,
                conversation_id=conversation_id,
                reviewed_by=reviewed_by if user_role == Role.DOCTOR.value else None,
                status=status_enum,
                db=db,
            )
        else:
            records, total = MedicalRecordService.list_medical_records(
                skip=skip,
                limit=limit,
                patient_id=patient_id,
                conversation_id=conversation_id,
                reviewed_by=reviewed_by if user_role == Role.DOCTOR.value else None,
                status=status_enum,
                db=db,
            )

        return MedicalRecordListResponse(total=total, items=_serialize_medical_records(records))
    except ValidationException as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"List medical records failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取病历列表失败",
        )


@router.get("/{record_id}", response_model=MedicalRecordResponse)
async def get_medical_record(
    record_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        user_id = current_user.get("id")
        user_role = current_user.get("role")

        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")

        if user_role == Role.PATIENT.value and medical_record.patient_id != user_id:
            raise AuthorizationException("无权访问该病历")

        if user_role == Role.DOCTOR.value and not _doctor_can_view_record(medical_record, user_id):
            raise AuthorizationException("无权访问该病历")

        return _serialize_medical_record(medical_record)
    except (NotFoundException, AuthorizationException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Get medical record failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取病历详情失败",
        )


@router.put("/{record_id}", response_model=MedicalRecordResponse)
async def update_medical_record(
    record_id: int,
    record_data: MedicalRecordUpdate,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        medical_record = MedicalRecordService.update_medical_record(record_id, record_data, db)
        return _serialize_medical_record(medical_record)
    except (NotFoundException, BusinessException, AuthorizationException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Update medical record failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新病历失败",
        )


@router.patch("/{record_id}/status", response_model=MedicalRecordResponse)
async def update_medical_record_status(
    record_id: int,
    status_data: MedicalRecordStatusUpdate,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        target_status = status_data.status
        if target_status == MedicalRecordStatus.CONFIRMED.value:
            medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
            if not medical_record:
                raise NotFoundException(f"病历 ID {record_id} 不存在")
            quality_check = _medical_record_quality_check(medical_record)
            if quality_check["level"] == "blocked":
                raise BusinessException("AI 质检未通过：" + "；".join(quality_check["blocking"]))
            metadata = dict(medical_record.extra_metadata or {})
            metadata["ai_quality_check"] = quality_check
            medical_record.extra_metadata = metadata

        medical_record = MedicalRecordService.update_medical_record_status(record_id, status_data, db)
        return _serialize_medical_record(medical_record)
    except (NotFoundException, ValidationException, BusinessException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Update medical record status failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新病历状态失败",
        )


@router.post("/{record_id}/review", response_model=MedicalRecordResponse)
async def review_medical_record(
    record_id: int,
    review_data: MedicalRecordReview,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        reviewer_id = current_user.get("id")
        medical_record = MedicalRecordService.review_medical_record(record_id, reviewer_id, review_data, db)
        return _serialize_medical_record(medical_record)
    except (NotFoundException, BusinessException, AuthorizationException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Review medical record failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="审核病历失败",
        )


@router.post("/{record_id}/archive", response_model=MedicalRecordResponse)
async def archive_medical_record(
    record_id: int,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        current_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not current_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")

        if _record_status_value(current_record) == MedicalRecordStatus.CONFIRMED.value:
            current_record.mark_as_archived()
            db.commit()
            db.refresh(current_record)
            medical_record = current_record
        else:
            medical_record = MedicalRecordService.archive_medical_record(record_id, db)
        return _serialize_medical_record(medical_record)
    except (NotFoundException, BusinessException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Archive medical record failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="归档病历失败",
        )


@router.get("/conversation/{conversation_id}/records", response_model=List[MedicalRecordResponse])
async def get_conversation_records(
    conversation_id: int,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        records = MedicalRecordService.get_conversation_records(conversation_id, db=db)
        if current_user.get("role") == Role.PATIENT.value:
            records = [record for record in records if record.patient_id == current_user.get("id")]
        return _serialize_medical_records(records)
    except Exception as exc:
        logger.error(f"Get conversation medical records failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话病历失败",
        )


@router.post("/{record_id}/quality-check")
async def quality_check_medical_record(
    record_id: int,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")

        quality_check = _medical_record_quality_check(medical_record)
        metadata = dict(medical_record.extra_metadata or {})
        metadata["ai_quality_check"] = quality_check
        medical_record.extra_metadata = metadata
        db.commit()
        return quality_check
    except (NotFoundException, BusinessException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Medical record quality check failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="病历质检失败",
        )


@router.post("/{record_id}/assist")
async def assist_medical_record(
    record_id: int,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")

        suggestions = _build_assisted_record_fields(medical_record)
        return {
            "source": "agent_assist",
            "suggestions": suggestions,
            "message": "AI 建议仅用于医生编辑参考，保存后才会进入病历。",
        }
    except NotFoundException as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Medical record assist failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="病历智能补全失败",
        )


@router.post("/{record_id}/agent-feedback")
async def submit_medical_record_agent_feedback(
    record_id: int,
    feedback: Dict[str, Any],
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        medical_record = MedicalRecordService.get_medical_record_by_id(record_id, db)
        if not medical_record:
            raise NotFoundException(f"病历 ID {record_id} 不存在")

        feedback_type = str(feedback.get("feedback_type") or "").strip()
        if feedback_type not in {"useful", "inaccurate", "missed_risk"}:
            raise ValidationException("Invalid feedback_type")

        entry = {
            "feedback_type": feedback_type,
            "comment": str(feedback.get("comment") or "").strip(),
            "doctor_id": current_user.get("id"),
            "record_id": record_id,
            "conversation_id": medical_record.conversation_id,
            "feedback_source": "doctor_review",
            "created_at": datetime.utcnow().isoformat(),
        }
        metadata = dict(medical_record.extra_metadata or {})
        feedback_items = list(metadata.get("agent_feedback") or [])
        feedback_items.append(entry)
        metadata["agent_feedback"] = feedback_items
        metadata["feedback_source"] = "doctor_review"
        medical_record.extra_metadata = metadata
        db.commit()
        return {"saved": True, "feedback": entry}
    except (NotFoundException, ValidationException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Medical record agent feedback failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="保存 Agent 反馈失败",
        )


@router.delete("/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_medical_record(
    record_id: int,
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    try:
        MedicalRecordService.delete_medical_record(record_id, db)
        return None
    except (NotFoundException, BusinessException) as exc:
        raise to_http_exception(exc)
    except Exception as exc:
        logger.error(f"Delete medical record failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除病历失败",
        )


__all__ = ["router"]
