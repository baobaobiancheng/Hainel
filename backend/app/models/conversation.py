"""
会话模型
定义医疗咨询会话相关的数据库模型
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


class ConversationStatus(str, Enum):
    """会话状态枚举"""
    PENDING = "pending"  # 待处理
    ACTIVE = "active"  # 进行中
    PAUSED = "paused"  # 已暂停
    COMPLETED = "completed"  # 已完成
    CANCELLED = "cancelled"  # 已取消


class ComplexityLevel(str, Enum):
    """复杂度级别枚举"""
    LOW = "low"  # 低复杂度
    MEDIUM = "medium"  # 中复杂度
    HIGH = "high"  # 高复杂度


class CollaborationMode(str, Enum):
    """协作模式枚举"""
    PCC = "pcc"  # 单智能体模式
    MDT = "mdt"  # 多学科团队模式
    ICT = "ict"  # 跨学科协作模式


class Conversation(BaseModel):
    """会话模型"""
    
    __tablename__ = "conversations"
    
    # 关联用户
    patient_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="患者ID",
    )
    doctor_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="医生ID（可选）",
    )
    
    # 会话基本信息
    title = Column(String(200), nullable=True, comment="会话标题")
    chief_complaint = Column(Text, nullable=True, comment="主诉")
    
    # 会话状态
    status = Column(
        SQLEnum(ConversationStatus, values_callable=lambda x: [e.value for e in x]),
        default=ConversationStatus.PENDING,
        nullable=False,
        index=True,
        comment="会话状态：pending/active/paused/completed/cancelled",
    )
    
    # 复杂度评估
    complexity_level = Column(
        SQLEnum(ComplexityLevel, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
        comment="复杂度级别：low/medium/high",
    )
    complexity_score = Column(Integer, nullable=True, comment="复杂度评分（0-100）")
    
    # 协作模式
    collaboration_mode = Column(
        SQLEnum(CollaborationMode, values_callable=lambda x: [e.value for e in x]),
        nullable=True,
        index=True,
        comment="协作模式：pcc/mdt/ict",
    )
    
    # 智能体信息
    agent_count = Column(Integer, default=1, nullable=False, comment="参与的智能体数量")
    agent_ids = Column(JSON, nullable=True, comment="智能体ID列表")
    
    # 统计信息
    message_count = Column(Integer, default=0, nullable=False, comment="消息数量")
    round_count = Column(Integer, default=0, nullable=False, comment="对话轮次")
    
    # 时间信息
    started_at = Column(DateTime, nullable=True, comment="开始时间")
    ended_at = Column(DateTime, nullable=True, comment="结束时间")
    last_message_at = Column(DateTime, nullable=True, comment="最后消息时间")
    
    # 元数据
    extra_metadata = Column(JSON, nullable=True, comment="扩展元数据")
    
    # 关系
    patient = relationship(
        "User",
        foreign_keys=[patient_id],
        back_populates="patient_conversations",
    )
    doctor = relationship(
        "User",
        foreign_keys=[doctor_id],
        back_populates="doctor_conversations",
    )
    messages = relationship(
        "Message",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="Message.created_at",
    )
    medical_records = relationship(
        "MedicalRecord",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )
    
    # 索引
    __table_args__ = (
        Index("idx_conversation_patient_status", "patient_id", "status"),
        Index("idx_conversation_doctor_status", "doctor_id", "status"),
        Index("idx_conversation_complexity_mode", "complexity_level", "collaboration_mode"),
    )
    
    def __repr__(self) -> str:
        """返回会话的字符串表示"""
        return f"<Conversation(id={self.id}, patient_id={self.patient_id}, status={self.status})>"
    
    def is_active(self) -> bool:
        """检查会话是否处于活跃状态"""
        return self.status == ConversationStatus.ACTIVE
    
    def is_completed(self) -> bool:
        """检查会话是否已完成"""
        return self.status == ConversationStatus.COMPLETED
    
    def mark_as_active(self):
        """标记会话为活跃状态"""
        self.status = ConversationStatus.ACTIVE
        if not self.started_at:
            self.started_at = datetime.utcnow()
    
    def mark_as_completed(self):
        """标记会话为已完成"""
        self.status = ConversationStatus.COMPLETED
        self.ended_at = datetime.utcnow()
    
    def mark_as_cancelled(self):
        """标记会话为已取消"""
        self.status = ConversationStatus.CANCELLED
        self.ended_at = datetime.utcnow()


# 导出
__all__ = [
    "Conversation",
    "ConversationStatus",
    "ComplexityLevel",
    "CollaborationMode",
]

