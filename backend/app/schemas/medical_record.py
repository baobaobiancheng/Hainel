"""
Medical-record-related Pydantic schemas.
"""
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict, AliasChoices


class MedicalRecordBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="病历标题")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    present_illness: Optional[str] = Field(None, description="现病史")
    past_history: Optional[str] = Field(None, description="既往史")
    physical_examination: Optional[str] = Field(None, description="体格检查")
    auxiliary_examination: Optional[str] = Field(None, description="辅助检查")
    diagnosis: Optional[List[Dict[str, Any]]] = Field(None, description="结构化诊断")
    treatment_plan: Optional[str] = Field(None, description="治疗方案")
    medications: Optional[List[Dict[str, Any]]] = Field(None, description="用药信息")
    medical_advice: Optional[str] = Field(None, description="医嘱")
    follow_up: Optional[str] = Field(None, description="随访建议")


class MedicalRecordCreate(MedicalRecordBase):
    patient_id: int = Field(..., description="患者ID")
    conversation_id: Optional[int] = Field(None, description="关联会话ID")
    content: Optional[Dict[str, Any]] = Field(None, description="完整病历内容")
    agent_name: Optional[str] = Field(None, max_length=100, description="生成病历的智能体名称")
    agent_id: Optional[str] = Field(None, max_length=100, description="生成病历的智能体ID")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        validation_alias=AliasChoices("extra_metadata", "metadata"),
        description="扩展元数据",
    )


class MedicalRecordUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=200, description="病历标题")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    present_illness: Optional[str] = Field(None, description="现病史")
    past_history: Optional[str] = Field(None, description="既往史")
    physical_examination: Optional[str] = Field(None, description="体格检查")
    auxiliary_examination: Optional[str] = Field(None, description="辅助检查")
    diagnosis: Optional[List[Dict[str, Any]]] = Field(None, description="结构化诊断")
    treatment_plan: Optional[str] = Field(None, description="治疗方案")
    medications: Optional[List[Dict[str, Any]]] = Field(None, description="用药信息")
    medical_advice: Optional[str] = Field(None, description="医嘱")
    follow_up: Optional[str] = Field(None, description="随访建议")
    content: Optional[Dict[str, Any]] = Field(None, description="完整病历内容")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")


class MedicalRecordResponse(MedicalRecordBase):
    id: int = Field(..., description="病历ID")
    patient_id: int = Field(..., description="患者ID")
    patient_name: Optional[str] = Field(None, description="患者姓名")
    conversation_id: Optional[int] = Field(None, description="关联会话ID")
    conversation_title: Optional[str] = Field(None, description="关联会话标题")
    reviewed_by: Optional[int] = Field(None, description="审核医生ID")
    status: str = Field(..., description="病历状态")
    content: Optional[Dict[str, Any]] = Field(None, description="完整病历内容")
    agent_name: Optional[str] = Field(None, description="生成病历的智能体名称")
    agent_id: Optional[str] = Field(None, description="生成病历的智能体ID")
    review_comment: Optional[str] = Field(None, description="审核意见")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    archived_at: Optional[datetime] = Field(None, description="归档时间")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")

    model_config = ConfigDict(from_attributes=True)


class MedicalRecordListResponse(BaseModel):
    total: int = Field(..., description="总数量")
    items: List[MedicalRecordResponse] = Field(..., description="病历列表")


class MedicalRecordStatusUpdate(BaseModel):
    status: str = Field(..., description="病历状态：draft/confirmed/reviewed/archived")


class MedicalRecordReview(BaseModel):
    review_comment: Optional[str] = Field(None, description="审核意见")
    approve: bool = Field(..., description="是否通过审核")


class MedicalRecordSummary(BaseModel):
    id: int = Field(..., description="病历ID")
    title: str = Field(..., description="病历标题")
    status: str = Field(..., description="病历状态")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    reviewed_at: Optional[datetime] = Field(None, description="审核时间")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(from_attributes=True)


class DiagnosisItem(BaseModel):
    name: str = Field(..., description="诊断名称")
    code: Optional[str] = Field(None, description="诊断编码")
    type: Optional[str] = Field(None, description="诊断类型")
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度")


class MedicationItem(BaseModel):
    name: str = Field(..., description="药品名称")
    dosage: Optional[str] = Field(None, description="剂量")
    frequency: Optional[str] = Field(None, description="频次")
    duration: Optional[str] = Field(None, description="用药时长")
    instructions: Optional[str] = Field(None, description="用药说明")


__all__ = [
    "MedicalRecordBase",
    "MedicalRecordCreate",
    "MedicalRecordUpdate",
    "MedicalRecordResponse",
    "MedicalRecordListResponse",
    "MedicalRecordStatusUpdate",
    "MedicalRecordReview",
    "MedicalRecordSummary",
    "DiagnosisItem",
    "MedicationItem",
]
