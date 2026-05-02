"""
Doctor-facing APIs for patients, conversations, and dashboard overview.
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.models.user import User
from app.models.conversation import Conversation, ConversationStatus
from app.models.medical_record import MedicalRecord, MedicalRecordStatus
from app.models.message import Message, MessageType
from app.core.permissions import get_current_user, require_role, Role
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/doctors", tags=["doctor"])


class PatientSummaryResponse(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool
    created_at: datetime
    conversation_count: int = Field(default=0)
    last_conversation_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ConversationSummaryResponse(BaseModel):
    id: int
    patient_id: int
    patient_name: Optional[str] = None
    title: Optional[str] = None
    chief_complaint: Optional[str] = None
    status: str
    complexity_level: Optional[str] = None
    collaboration_mode: Optional[str] = None
    message_count: int
    last_message_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardKpis(BaseModel):
    today_consultations: int
    active_conversations: int
    urgent_triage_count: int
    pending_confirmation_records: int
    confirmed_records: int
    archived_records: int
    pending_review_records: int = 0


class DashboardPoint(BaseModel):
    date: str
    value: int


class DashboardQueueItem(BaseModel):
    type: str
    id: int
    title: str
    subtitle: Optional[str] = None
    priority: str
    status: str
    conversation_id: Optional[int] = None
    patient_id: Optional[int] = None


class DashboardOverviewResponse(BaseModel):
    range: str
    kpis: DashboardKpis
    consultation_trend: List[DashboardPoint]
    triage_distribution: List[Dict[str, Any]]
    department_distribution: List[Dict[str, Any]]
    record_status_distribution: List[Dict[str, Any]]
    doctor_queue: List[DashboardQueueItem]
    report_upload_trend: List[DashboardPoint]


def _normalize_metadata(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    extra_metadata = getattr(value, "extra_metadata", None)
    if isinstance(extra_metadata, dict):
        return extra_metadata
    metadata = getattr(value, "metadata", None)
    if isinstance(metadata, dict):
        return metadata
    return {}


def _date_range_points(range_key: str) -> List[str]:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(range_key, 7)
    today = datetime.now().date()
    return [
        (today - timedelta(days=offset)).isoformat()
        for offset in reversed(range(days - 1, -1, -1))
    ]


def _get_doctor_scoped_conversations(
    db: Session,
    user_role: str,
    doctor_id: int,
) -> List[Conversation]:
    query = db.query(Conversation)
    if user_role != Role.ADMIN.value:
        query = query.filter(Conversation.doctor_id == doctor_id)
    return query.all()


@router.get("/patients", response_model=List[PatientSummaryResponse])
async def get_doctor_patients(
    conv_status: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    doctor_id = current_user.get("id")
    user_role = current_user.get("role")

    conv_query = db.query(Conversation.patient_id).distinct()
    if user_role != Role.ADMIN.value:
        conv_query = conv_query.filter(Conversation.doctor_id == doctor_id)
    if conv_status:
        try:
            conv_query = conv_query.filter(Conversation.status == ConversationStatus(conv_status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的会话状态: {conv_status}")

    patient_ids = [row[0] for row in conv_query.all()]
    if not patient_ids:
        return []

    user_query = db.query(User).filter(User.id.in_(patient_ids), User.role == Role.PATIENT)
    if search:
        user_query = user_query.filter(
            (User.username.ilike(f"%{search}%")) | (User.full_name.ilike(f"%{search}%"))
        )

    users = (
        user_query.order_by(User.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    result: List[PatientSummaryResponse] = []
    for user in users:
        conv_count_query = db.query(Conversation).filter(Conversation.patient_id == user.id)
        if user_role != Role.ADMIN.value:
            conv_count_query = conv_count_query.filter(Conversation.doctor_id == doctor_id)
        conv_count = conv_count_query.count()
        last_conv = (
            conv_count_query.order_by(
                func.isnull(Conversation.last_message_at),
                Conversation.last_message_at.desc()
            ).first()
        )
        result.append(
            PatientSummaryResponse(
                id=user.id,
                username=user.username,
                full_name=user.full_name,
                phone=user.phone,
                email=user.email,
                avatar_url=user.avatar_url,
                is_active=user.is_active,
                created_at=user.created_at,
                conversation_count=conv_count,
                last_conversation_at=last_conv.last_message_at if last_conv else None,
            )
        )
    return result


@router.get("/conversations", response_model=List[ConversationSummaryResponse])
async def get_doctor_conversations(
    conv_status: Optional[str] = Query(None, alias="status"),
    patient_id: Optional[int] = Query(None),
    complexity: Optional[str] = Query(None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    doctor_id = current_user.get("id")
    user_role = current_user.get("role")

    query = db.query(Conversation)
    if user_role != Role.ADMIN.value:
        query = query.filter(Conversation.doctor_id == doctor_id)
    if conv_status:
        try:
            query = query.filter(Conversation.status == ConversationStatus(conv_status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的会话状态: {conv_status}")
    if patient_id:
        query = query.filter(Conversation.patient_id == patient_id)
    if complexity:
        query = query.filter(Conversation.complexity_level == complexity)

    conversations = (
        query.order_by(
            func.isnull(Conversation.last_message_at),
            Conversation.last_message_at.desc()
        )
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    patient_ids = list({conversation.patient_id for conversation in conversations})
    patient_map: Dict[int, User] = {
        user.id: user
        for user in db.query(User).filter(User.id.in_(patient_ids)).all()
    }

    return [
        ConversationSummaryResponse(
            id=conversation.id,
            patient_id=conversation.patient_id,
            patient_name=(
                (patient_map[conversation.patient_id].full_name or patient_map[conversation.patient_id].username)
                if conversation.patient_id in patient_map else None
            ),
            title=conversation.title,
            chief_complaint=conversation.chief_complaint,
            status=conversation.status.value,
            complexity_level=conversation.complexity_level.value if conversation.complexity_level else None,
            collaboration_mode=conversation.collaboration_mode.value if conversation.collaboration_mode else None,
            message_count=conversation.message_count,
            last_message_at=conversation.last_message_at,
            created_at=conversation.created_at,
        )
        for conversation in conversations
    ]


@router.get("/patients/{patient_id}/summary")
async def get_patient_summary(
    patient_id: int,
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    doctor_id = current_user.get("id")
    user_role = current_user.get("role")

    patient = db.query(User).filter(User.id == patient_id, User.role == Role.PATIENT).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="患者不存在")

    conversation_query = db.query(Conversation).filter(Conversation.patient_id == patient_id)
    if user_role != Role.ADMIN.value:
        conversation_query = conversation_query.filter(Conversation.doctor_id == doctor_id)
    conversations = conversation_query.order_by(Conversation.created_at.desc()).all()

    conversation_ids = [conversation.id for conversation in conversations]
    medical_record_query = db.query(MedicalRecord).filter(MedicalRecord.patient_id == patient_id)
    if conversation_ids:
        medical_record_query = medical_record_query.filter(MedicalRecord.conversation_id.in_(conversation_ids))
    medical_records = medical_record_query.all()

    conversation_stats = {
        "total": len(conversations),
        "active": sum(1 for c in conversations if c.status == ConversationStatus.ACTIVE),
        "completed": sum(1 for c in conversations if c.status == ConversationStatus.COMPLETED),
        "pending": sum(1 for c in conversations if c.status == ConversationStatus.PENDING),
        "cancelled": sum(1 for c in conversations if c.status == ConversationStatus.CANCELLED),
    }
    medical_record_stats = {
        "total": len(medical_records),
        "draft": sum(1 for r in medical_records if r.status == MedicalRecordStatus.DRAFT),
        "confirmed": sum(1 for r in medical_records if r.status == MedicalRecordStatus.CONFIRMED),
        "reviewed": sum(1 for r in medical_records if r.status == MedicalRecordStatus.REVIEWED),
        "archived": sum(1 for r in medical_records if r.status == MedicalRecordStatus.ARCHIVED),
    }

    start_date = datetime.now().date() - timedelta(days=29)
    conversation_counter: Counter[str] = Counter()
    record_counter: Counter[str] = Counter()
    for conversation in conversations:
        created_day = conversation.created_at.date()
        if created_day >= start_date:
            conversation_counter[created_day.isoformat()] += 1
    for record in medical_records:
        created_day = record.created_at.date()
        if created_day >= start_date:
            record_counter[created_day.isoformat()] += 1

    activity_trend = []
    for date_key in _date_range_points("30d"):
        activity_trend.append(
            {
                "date": date_key,
                "consultations": conversation_counter.get(date_key, 0),
                "records": record_counter.get(date_key, 0),
            }
        )

    return {
        "patient": {
            "id": patient.id,
            "username": patient.username,
            "full_name": patient.full_name,
            "phone": patient.phone,
            "email": patient.email,
            "avatar_url": patient.avatar_url,
            "is_active": patient.is_active,
            "created_at": patient.created_at.isoformat(),
            "health_profile": patient.health_profile if isinstance(patient.health_profile, dict) else {},
        },
        "conversation_stats": conversation_stats,
        "medical_record_stats": medical_record_stats,
        "activity_trend": activity_trend,
        "recent_conversations": [
            {
                "id": conversation.id,
                "title": conversation.title,
                "chief_complaint": conversation.chief_complaint,
                "status": conversation.status.value,
                "complexity_level": conversation.complexity_level.value if conversation.complexity_level else None,
                "collaboration_mode": conversation.collaboration_mode.value if conversation.collaboration_mode else None,
                "message_count": conversation.message_count,
                "last_message_at": conversation.last_message_at.isoformat() if conversation.last_message_at else None,
                "created_at": conversation.created_at.isoformat(),
            }
            for conversation in conversations[:8]
        ],
    }


@router.get("/dashboard-overview", response_model=DashboardOverviewResponse)
async def get_dashboard_overview(
    range: str = Query("7d", pattern="^(7d|30d|90d)$"),
    current_user: dict = Depends(get_current_user),
    _: None = Depends(require_role([Role.DOCTOR, Role.ADMIN])),
    db: Session = Depends(get_db),
):
    doctor_id = current_user.get("id")
    user_role = current_user.get("role")
    scoped_conversations = _get_doctor_scoped_conversations(db, user_role, doctor_id)
    conversation_ids = [conversation.id for conversation in scoped_conversations]

    if user_role == Role.ADMIN.value:
        scoped_records = db.query(MedicalRecord).all()
    elif conversation_ids:
        scoped_records = db.query(MedicalRecord).filter(MedicalRecord.conversation_id.in_(conversation_ids)).all()
    else:
        scoped_records = []

    range_days = {"7d": 7, "30d": 30, "90d": 90}[range]
    start_date = datetime.now().date() - timedelta(days=range_days - 1)
    point_keys = _date_range_points(range)

    conversation_counter: Counter[str] = Counter()
    triage_counter: Counter[str] = Counter()
    department_counter: Counter[str] = Counter()
    urgent_conversations: List[Conversation] = []
    for conversation in scoped_conversations:
        created_day = conversation.created_at.date()
        if created_day >= start_date:
            conversation_counter[created_day.isoformat()] += 1

        metadata = _normalize_metadata(conversation)
        triage = _normalize_metadata(metadata.get("triage"))
        urgency = str(triage.get("urgency") or "").strip()
        department = str(triage.get("department_name") or triage.get("department") or "").strip()
        if urgency:
            triage_counter[urgency] += 1
            if urgency in {"high", "urgent"}:
                urgent_conversations.append(conversation)
        if department:
            department_counter[department] += 1

    record_status_counter: Counter[str] = Counter()
    for record in scoped_records:
        record_status_counter[str(record.status.value if hasattr(record.status, "value") else record.status)] += 1

    report_counter: Counter[str] = Counter()
    if conversation_ids:
        report_messages = (
            db.query(Message)
            .filter(
                Message.conversation_id.in_(conversation_ids),
                Message.message_type == MessageType.FILE,
            )
            .all()
        )
        for message in report_messages:
            created_day = message.created_at.date()
            if created_day >= start_date:
                report_counter[created_day.isoformat()] += 1

    patient_map: Dict[int, User] = {
        user.id: user
        for user in db.query(User).filter(User.id.in_({conversation.patient_id for conversation in scoped_conversations})).all()
    } if scoped_conversations else {}

    queue_items: List[DashboardQueueItem] = []
    for conversation in sorted(
        urgent_conversations,
        key=lambda item: item.last_message_at or item.created_at,
        reverse=True,
    )[:4]:
        patient = patient_map.get(conversation.patient_id)
        metadata = _normalize_metadata(conversation)
        triage = _normalize_metadata(metadata.get("triage"))
        queue_items.append(
            DashboardQueueItem(
                type="conversation",
                id=conversation.id,
                title=conversation.chief_complaint or conversation.title or f"会话 #{conversation.id}",
                subtitle=(patient.full_name or patient.username) if patient else None,
                priority=str(triage.get("urgency") or "high"),
                status=conversation.status.value,
                conversation_id=conversation.id,
                patient_id=conversation.patient_id,
            )
        )

    for record in sorted(scoped_records, key=lambda item: item.updated_at, reverse=True):
        if record.status != MedicalRecordStatus.DRAFT:
            continue
        patient = patient_map.get(record.patient_id)
        queue_items.append(
            DashboardQueueItem(
                type="record",
                id=record.id,
                title=record.title,
                subtitle=(patient.full_name or patient.username) if patient else None,
                priority="normal",
                status=record.status.value,
                conversation_id=record.conversation_id,
                patient_id=record.patient_id,
            )
        )
        if len(queue_items) >= 8:
            break

    today = datetime.now().date()
    recent_patient_ids = {
        conversation.patient_id
        for conversation in scoped_conversations
        if conversation.created_at.date() >= start_date
    }

    return DashboardOverviewResponse(
        range=range,
        kpis=DashboardKpis(
            today_consultations=sum(1 for conversation in scoped_conversations if conversation.created_at.date() == today),
            active_conversations=sum(1 for conversation in scoped_conversations if conversation.status == ConversationStatus.ACTIVE),
            urgent_triage_count=sum(triage_counter.get(key, 0) for key in ("high", "urgent")),
            pending_confirmation_records=record_status_counter.get("draft", 0),
            confirmed_records=record_status_counter.get("confirmed", 0),
            archived_records=record_status_counter.get("archived", 0),
            pending_review_records=0,
        ),
        consultation_trend=[DashboardPoint(date=key, value=conversation_counter.get(key, 0)) for key in point_keys],
        triage_distribution=[
            {"label": key, "value": value}
            for key, value in triage_counter.items()
        ],
        department_distribution=[
            {"label": key, "value": value}
            for key, value in department_counter.items()
        ],
        record_status_distribution=[
            {"label": key, "value": value}
            for key, value in record_status_counter.items()
        ],
        doctor_queue=queue_items,
        report_upload_trend=[DashboardPoint(date=key, value=report_counter.get(key, 0)) for key in point_keys],
    )


__all__ = ["router"]
