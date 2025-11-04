"""
知识点模型
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class KnowledgePoint(Base):
    """知识点表"""
    __tablename__ = "knowledge_points"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # 基本信息
    name: Mapped[str] = mapped_column(String(100), index=True)
    code: Mapped[str | None] = mapped_column(String(50), unique=True, nullable=True)  # 编码
    subject: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 层级关系
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_points.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    level: Mapped[int] = mapped_column(default=1)  # 层级（1为顶层）
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # 关系
    parent: Mapped[Optional["KnowledgePoint"]] = relationship(
        "KnowledgePoint",
        remote_side=[id],
        back_populates="children",
    )
    
    children: Mapped[List["KnowledgePoint"]] = relationship(
        "KnowledgePoint",
        back_populates="parent",
        cascade="all, delete-orphan",
    )
    
    question_mappings: Mapped[List["QuestionKnowledgeMapping"]] = relationship(
        "QuestionKnowledgeMapping",
        back_populates="knowledge_point",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<KnowledgePoint {self.name}>"


class QuestionKnowledgeMapping(Base):
    """错题-知识点关联表"""
    __tablename__ = "question_knowledge_mappings"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    
    # 外键
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_questions.id", ondelete="CASCADE"),
        index=True,
    )
    
    knowledge_point_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_points.id", ondelete="CASCADE"),
        index=True,
    )
    
    # 关联度
    relevance_score: Mapped[float] = mapped_column(default=1.0)  # 0-1
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    error_question: Mapped["ErrorQuestion"] = relationship(
        "ErrorQuestion",
        back_populates="knowledge_mappings",
    )
    
    knowledge_point: Mapped["KnowledgePoint"] = relationship(
        "KnowledgePoint",
        back_populates="question_mappings",
    )
    
    def __repr__(self) -> str:
        return f"<Mapping Q:{self.question_id} - K:{self.knowledge_point_id}>"

