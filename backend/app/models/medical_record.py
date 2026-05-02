"""
病历模型
定义医疗病历相关的数据库模型
"""
from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    Enum as SQLEnum,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class MedicalRecordStatus(str, Enum):
    """病历状态枚举"""
    DRAFT = "draft"  # 草稿
    CONFIRMED = "confirmed"  # 已确认
    REVIEWED = "reviewed"  # 已审核
    ARCHIVED = "archived"  # 已归档


class MedicalRecord(BaseModel):
    """病历模型"""
    
    __tablename__ = "medical_records"
    
    # 关联患者
    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="患者ID",
    )
    
    # 关联会话（可选）
    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="关联的会话ID",
    )
    
    # 审核医生
    reviewed_by = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="审核医生ID",
    )
    
    # 病历基本信息
    title = Column(String(200), nullable=False, comment="病历标题")
    
    # 病历状态
    status = Column(
        SQLEnum(MedicalRecordStatus, values_callable=lambda x: [e.value for e in x]),
        default=MedicalRecordStatus.DRAFT,
        nullable=False,
        index=True,
        comment="病历状态：draft/confirmed/reviewed/archived",
    )
    
    # 结构化病历数据
    # 主诉
    chief_complaint = Column(Text, nullable=True, comment="主诉")
    
    # 现病史
    present_illness = Column(Text, nullable=True, comment="现病史")
    
    # 既往史
    past_history = Column(Text, nullable=True, comment="既往史")
    
    # 体格检查
    physical_examination = Column(Text, nullable=True, comment="体格检查")
    
    # 辅助检查
    auxiliary_examination = Column(Text, nullable=True, comment="辅助检查")
    
    # 诊断
    diagnosis = Column(JSON, nullable=True, comment="诊断（JSON格式，支持多个诊断）")
    
    # 治疗方案
    treatment_plan = Column(Text, nullable=True, comment="治疗方案")
    
    # 用药信息
    medications = Column(JSON, nullable=True, comment="用药信息（JSON格式）")
    
    # 医嘱
    medical_advice = Column(Text, nullable=True, comment="医嘱")
    
    # 随访建议
    follow_up = Column(Text, nullable=True, comment="随访建议")
    
    # 完整病历内容（JSON格式，包含所有结构化数据）
    content = Column(JSON, nullable=True, comment="完整病历内容（JSON格式）")
    
    # 智能体信息
    agent_name = Column(String(100), nullable=True, comment="生成病历的智能体名称")
    agent_id = Column(String(100), nullable=True, comment="生成病历的智能体ID")
    
    # 审核信息
    review_comment = Column(Text, nullable=True, comment="审核意见")
    reviewed_at = Column(DateTime, nullable=True, comment="审核时间")
    
    # 归档信息
    archived_at = Column(DateTime, nullable=True, comment="归档时间")
    
    # 元数据
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据")
    
    # 关系
    patient = relationship(
        "User",
        foreign_keys=[patient_id],
        back_populates="medical_records",
    )
    conversation = relationship(
        "Conversation",
        back_populates="medical_records",
    )
    reviewer = relationship(
        "User",
        foreign_keys=[reviewed_by],
        back_populates="reviewed_records",
    )
    
    # 索引
    __table_args__ = (
        Index("idx_medical_record_patient_status", "patient_id", "status"),
        Index("idx_medical_record_conversation", "conversation_id"),
        Index("idx_medical_record_reviewed", "reviewed_by", "status"),
    )
    
    def __repr__(self) -> str:
        """返回病历的字符串表示"""
        return f"<MedicalRecord(id={self.id}, patient_id={self.patient_id}, status={self.status})>"
    
    def is_draft(self) -> bool:
        """检查病历是否为草稿"""
        return self.status == MedicalRecordStatus.DRAFT
    
    def is_confirmed(self) -> bool:
        """检查病历是否已确认"""
        return self.status == MedicalRecordStatus.CONFIRMED
    
    def is_reviewed(self) -> bool:
        """检查病历是否已审核"""
        return self.status == MedicalRecordStatus.REVIEWED
    
    def is_archived(self) -> bool:
        """检查病历是否已归档"""
        return self.status == MedicalRecordStatus.ARCHIVED
    
    def mark_as_confirmed(self):
        """标记病历为已确认"""
        self.status = MedicalRecordStatus.CONFIRMED
    
    def mark_as_reviewed(self, reviewer_id: int, comment: str = None):
        """
        标记病历为已审核
        
        Args:
            reviewer_id: 审核医生ID
            comment: 审核意见
        """
        self.status = MedicalRecordStatus.REVIEWED
        self.reviewed_by = reviewer_id
        self.review_comment = comment
        self.reviewed_at = datetime.utcnow()
    
    def mark_as_archived(self):
        """标记病历为已归档"""
        self.status = MedicalRecordStatus.ARCHIVED
        self.archived_at = datetime.utcnow()


# 导出
__all__ = [
    "MedicalRecord",
    "MedicalRecordStatus",
]

