"""
错题相关 Schema
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict
from app.models.error_question import DifficultyLevel, ErrorType


class ErrorQuestionBase(BaseModel):
    """错题基础模型"""
    subject: str = Field(..., max_length=50, description="学科")
    chapter: Optional[str] = Field(None, max_length=100, description="章节")
    question_text: Optional[str] = Field(None, description="题目内容")
    question_image_url: Optional[str] = Field(None, description="题目图片URL")
    correct_answer: Optional[str] = Field(None, description="正确答案")
    user_answer: Optional[str] = Field(None, description="用户答案")
    explanation: Optional[str] = Field(None, description="解析")
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    error_type: ErrorType = ErrorType.OTHER
    tags: Optional[List[str]] = Field(None, description="标签列表")


class ErrorQuestionCreate(ErrorQuestionBase):
    """创建错题模型"""
    pass


class ErrorQuestionUpdate(BaseModel):
    """更新错题模型"""
    subject: Optional[str] = None
    chapter: Optional[str] = None
    question_text: Optional[str] = None
    question_image_url: Optional[str] = None
    correct_answer: Optional[str] = None
    user_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    error_type: Optional[ErrorType] = None
    tags: Optional[List[str]] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None


class ErrorQuestionResponse(ErrorQuestionBase):
    """错题响应模型"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    review_count: int
    mastery_level: float
    last_reviewed_at: Optional[datetime] = None
    next_review_at: Optional[datetime] = None
    is_archived: bool
    is_favorite: bool
    created_at: datetime
    updated_at: datetime


class ErrorQuestionFilter(BaseModel):
    """错题筛选模型"""
    subject: Optional[str] = None
    chapter: Optional[str] = None
    difficulty: Optional[DifficultyLevel] = None
    error_type: Optional[ErrorType] = None
    is_favorite: Optional[bool] = None
    is_archived: Optional[bool] = None
    tags: Optional[List[str]] = None
    
    # 排序
    sort_by: str = "created_at"  # created_at, updated_at, mastery_level
    sort_order: str = "desc"  # asc, desc

