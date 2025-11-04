"""
AI 分析记录模型
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class AIAnalysis(Base):
    """AI 分析记录表"""
    __tablename__ = "ai_analyses"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # 错题关联
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_questions.id", ondelete="CASCADE"),
        index=True,
    )
    
    # 分析类型
    analysis_type: Mapped[str] = mapped_column(
        String(50),
        index=True,
    )  # error_analysis, similar_questions, explanation, knowledge_extraction
    
    # 分析结果
    analysis_result: Mapped[dict] = mapped_column(JSONB)
    
    # AI 模型信息
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    # 状态
    status: Mapped[str] = mapped_column(String(20), default="completed")  # pending, completed, failed
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    
    # 关系
    error_question: Mapped["ErrorQuestion"] = relationship(
        "ErrorQuestion",
        back_populates="ai_analyses",
    )
    
    def __repr__(self) -> str:
        return f"<AIAnalysis {self.analysis_type} for Q:{self.question_id}>"

