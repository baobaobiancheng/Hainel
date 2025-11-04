"""
练习记录模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class PracticeRecord(Base):
    """练习记录表"""
    __tablename__ = "practice_records"
    
    # 主键
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    
    # 用户关联
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    
    # 题目关联
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("error_questions.id", ondelete="CASCADE"),
        index=True,
    )
    
    # 练习数据
    is_correct: Mapped[bool] = mapped_column(Boolean)
    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    time_spent: Mapped[int] = mapped_column(Integer)  # 用时（秒）
    
    # 置信度
    confidence: Mapped[float | None] = mapped_column(default=None, nullable=True)  # 0-1
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="practice_records")
    
    error_question: Mapped["ErrorQuestion"] = relationship(
        "ErrorQuestion",
        back_populates="practice_records",
    )
    
    def __repr__(self) -> str:
        return f"<PracticeRecord U:{self.user_id} - Q:{self.question_id}>"

