"""
Conversation-related Pydantic schemas.
"""
from datetime import datetime, date
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class ConversationBase(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="会话标题")
    chief_complaint: Optional[str] = Field(None, description="主诉")


class ConversationCreate(ConversationBase):
    patient_id: Optional[int] = Field(None, description="患者ID")
    doctor_id: Optional[int] = Field(None, description="医生ID")
    chief_complaint: str = Field(..., description="主诉")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class ConversationUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200, description="会话标题")
    status: Optional[str] = Field(None, description="会话状态")
    doctor_id: Optional[int] = Field(None, description="医生ID")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    extra_metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class ConversationResponse(ConversationBase):
    id: int = Field(..., description="会话ID")
    patient_id: int = Field(..., description="患者ID")
    doctor_id: Optional[int] = Field(None, description="医生ID")
    status: str = Field(..., description="会话状态")
    complexity_level: Optional[str] = Field(None, description="复杂度级别")
    complexity_score: Optional[int] = Field(None, ge=0, le=100, description="复杂度评分")
    collaboration_mode: Optional[str] = Field(None, description="协作模式")
    agent_count: int = Field(default=1, description="参与智能体数量")
    agent_ids: Optional[List[str]] = Field(None, description="智能体ID列表")
    message_count: int = Field(default=0, description="消息数量")
    round_count: int = Field(default=0, description="轮次")
    started_at: Optional[datetime] = Field(None, description="开始时间")
    ended_at: Optional[datetime] = Field(None, description="结束时间")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias=AliasChoices("extra_metadata", "metadata"),
        description="扩展元数据",
    )
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class ConversationListResponse(BaseModel):
    total: Optional[int] = Field(None, description="总数")
    items: List[ConversationResponse] = Field(..., description="会话列表")
    has_next: bool = Field(..., description="是否还有下一页")


class ConversationStatusUpdate(BaseModel):
    status: str = Field(..., description="会话状态")


class ConversationComplexityUpdate(BaseModel):
    complexity_level: str = Field(..., description="复杂度级别")
    complexity_score: Optional[int] = Field(None, ge=0, le=100, description="复杂度评分")
    collaboration_mode: str = Field(..., description="协作模式")
    agent_ids: Optional[List[str]] = Field(None, description="智能体ID列表")


class ConversationSummary(BaseModel):
    id: int = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    status: str = Field(..., description="会话状态")
    message_count: int = Field(..., description="消息数量")
    last_message_at: Optional[datetime] = Field(None, description="最后消息时间")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class DiagnosisContextConversation(BaseModel):
    id: int = Field(..., description="会话ID")
    title: Optional[str] = Field(None, description="会话标题")
    status: str = Field(..., description="会话状态")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")


class DiagnosisContextPatient(BaseModel):
    id: int = Field(..., description="患者ID")
    name: Optional[str] = Field(None, description="患者姓名")
    gender: Optional[str] = Field(None, description="性别")
    age: Optional[int] = Field(None, description="年龄")


class DiagnosisContextLinkedReport(BaseModel):
    message_id: Optional[int] = Field(None, description="消息ID")
    file_name: Optional[str] = Field(None, description="文件名")
    file_type: Optional[str] = Field(None, description="文件类型")
    report_type: Optional[str] = Field(None, description="报告类型")
    ocr_text: str = Field(default="", description="OCR文本")


class DiagnosisContextKnowledgeItem(BaseModel):
    source: str = Field(..., description="来源实体")
    relation: str = Field(..., description="关系编码")
    relation_label: str = Field(..., description="关系标签")
    target: str = Field(..., description="目标实体")
    target_category: str = Field(..., description="目标实体类别")


class DiagnosisContextKnowledgeGroup(BaseModel):
    key: str = Field(..., description="分组键")
    title: str = Field(..., description="分组标题")
    category: str = Field(..., description="分组类别")
    items: List[DiagnosisContextKnowledgeItem] = Field(default_factory=list, description="分组条目")


class DiagnosisContextKnowledgeContext(BaseModel):
    summary: str = Field(default="", description="知识图谱摘要")
    groups: List[DiagnosisContextKnowledgeGroup] = Field(default_factory=list, description="知识分组")


class DiagnosisContextLatestDiagnosis(BaseModel):
    message_id: int = Field(..., description="消息ID")
    content: str = Field(..., description="诊断内容")
    difficulty: Optional[str] = Field(None, description="诊断复杂度")
    agents_used: Optional[int | str] = Field(None, description="参与智能体数量")
    red_flags: List[Dict[str, Any]] = Field(default_factory=list, description="红旗症状")
    action_checklist: Optional[Dict[str, Any]] = Field(None, description="行动清单")
    kg_context: Optional[DiagnosisContextKnowledgeContext] = Field(None, description="知识图谱上下文")
    triage: Optional[Dict[str, Any]] = Field(None, description="分诊信息")
    team_recruitment: Optional[str] = Field(None, description="团队招募信息")
    expert_opinions: List[Dict[str, Any]] = Field(default_factory=list, description="专家意见")
    mdt_plan: Optional[str] = Field(None, description="MDT方案")
    team_reports: List[Dict[str, Any]] = Field(default_factory=list, description="团队报告")
    created_at: datetime = Field(..., description="创建时间")


class DiagnosisContextMedicalRecord(BaseModel):
    id: int = Field(..., description="病历ID")
    title: str = Field(..., description="病历标题")
    status: str = Field(..., description="病历状态")
    updated_at: datetime = Field(..., description="更新时间")


class DiagnosisContextResponse(BaseModel):
    conversation: DiagnosisContextConversation
    patient: DiagnosisContextPatient
    health_profile: Dict[str, Any] = Field(default_factory=dict, description="健康档案")
    structured_intake: Dict[str, Any] = Field(default_factory=dict, description="结构化问诊")
    triage: Optional[Dict[str, Any]] = Field(None, description="分诊信息")
    linked_reports: List[DiagnosisContextLinkedReport] = Field(default_factory=list, description="关联报告")
    latest_diagnosis: Optional[DiagnosisContextLatestDiagnosis] = Field(None, description="最新诊断")
    medical_records: List[DiagnosisContextMedicalRecord] = Field(default_factory=list, description="关联病历")


class MedicalRecordDraftRecord(BaseModel):
    title: str = Field(..., description="病历标题")
    status: str = Field(default="draft", description="病历状态")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    present_illness: Optional[str] = Field(None, description="现病史")
    past_history: Optional[str] = Field(None, description="既往史")
    physical_examination: Optional[str] = Field(None, description="体格检查")
    auxiliary_examination: Optional[str] = Field(None, description="辅助检查")
    preliminary_diagnosis: Optional[str] = Field(None, description="初步诊断摘要")
    diagnosis: List[Dict[str, Any]] = Field(default_factory=list, description="结构化诊断")
    treatment_plan: Optional[str] = Field(None, description="处理方案")
    medications: List[Dict[str, Any]] = Field(default_factory=list, description="用药信息")
    medical_advice: Optional[str] = Field(None, description="医嘱")
    follow_up: Optional[str] = Field(None, description="随访建议")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="草稿元数据")


class MedicalRecordDraftResponse(BaseModel):
    patient: DiagnosisContextPatient
    conversation: DiagnosisContextConversation
    draft_record: MedicalRecordDraftRecord


def calculate_age_from_birth_date(birth_date: Any) -> Optional[int]:
    if not birth_date:
        return None
    parsed: Optional[date] = None
    if isinstance(birth_date, datetime):
        parsed = birth_date.date()
    elif isinstance(birth_date, date):
        parsed = birth_date
    elif isinstance(birth_date, str):
        try:
            parsed = datetime.fromisoformat(birth_date.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    if not parsed:
        return None
    today = date.today()
    age = today.year - parsed.year - ((today.month, today.day) < (parsed.month, parsed.day))
    return age if age >= 0 else None


__all__ = [
    "ConversationBase",
    "ConversationCreate",
    "ConversationUpdate",
    "ConversationResponse",
    "ConversationListResponse",
    "ConversationStatusUpdate",
    "ConversationComplexityUpdate",
    "ConversationSummary",
    "DiagnosisContextConversation",
    "DiagnosisContextPatient",
    "DiagnosisContextLinkedReport",
    "DiagnosisContextKnowledgeItem",
    "DiagnosisContextKnowledgeGroup",
    "DiagnosisContextKnowledgeContext",
    "DiagnosisContextLatestDiagnosis",
    "DiagnosisContextMedicalRecord",
    "DiagnosisContextResponse",
    "MedicalRecordDraftRecord",
    "MedicalRecordDraftResponse",
    "calculate_age_from_birth_date",
]
