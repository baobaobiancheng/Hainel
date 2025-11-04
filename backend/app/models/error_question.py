"""
错题模型
"""
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum

from app.core.database import Base


class DifficultyLevel(str, enum.Enum):
    """难度等级"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ErrorType(str, enum.Enum):
    """错误类型"""
    CONCEPT = "concept"  # 概念理解错误
    CALCULATION = "calculation"  # 计算错误
    CARELESS = "careless"  # 粗心错误
    METHOD = "method"  # 方法错误
    OTHER = "other"  # 其他


class ErrorQuestion(Base):
    """错题表"""
    __tablename__ = "error_questions"
    
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
    
    # 题目基本信息
    subject: Mapped[str] = mapped_column(String(50), index=True)  # 学科
    chapter: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 章节
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # 题目文本
    question_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # 题目图片
    
    # 答案信息
    correct_answer: Mapped[str | None] = mapped_column(Text, nullable=True)  # 正确答案
    user_answer: Mapped[str | None] = mapped_column(Text, nullable=True)  # 用户答案
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)  # 解析
    
    # 分类与标签
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel),
        default=DifficultyLevel.MEDIUM,
        index=True,
    )
    error_type: Mapped[ErrorType] = mapped_column(
        SQLEnum(ErrorType),
        default=ErrorType.OTHER,
        index=True,
    )
    tags: Mapped[str | None] = mapped_column(String(500), nullable=True)  # JSON数组字符串
    
    # 学习数据
    review_count: Mapped[int] = mapped_column(Integer, default=0)  # 复习次数
    mastery_level: Mapped[float] = mapped_column(Float, default=0.0)  # 掌握程度 0-1
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    
    # 状态
    is_archived: Mapped[bool] = mapped_column(default=False)  # 是否归档
    is_favorite: Mapped[bool] = mapped_column(default=False)  # 是否收藏
    
    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )
    
    # 关系
    user: Mapped["User"] = relationship("User", back_populates="error_questions")
    
    ai_analyses: Mapped[List["AIAnalysis"]] = relationship(
        "AIAnalysis",
        back_populates="error_question",
        cascade="all, delete-orphan",
    )
    
    knowledge_mappings: Mapped[List["QuestionKnowledgeMapping"]] = relationship(
        "QuestionKnowledgeMapping",
        back_populates="error_question",
        cascade="all, delete-orphan",
    )
    
    practice_records: Mapped[List["PracticeRecord"]] = relationship(
        "PracticeRecord",
        back_populates="error_question",
        cascade="all, delete-orphan",
    )
    
    def __repr__(self) -> str:
        return f"<ErrorQuestion {self.id} - {self.subject}>"

