"""
数据库模型模块
"""
from app.models.user import User, UserRole
from app.models.error_question import ErrorQuestion, DifficultyLevel, ErrorType
from app.models.knowledge_point import KnowledgePoint, QuestionKnowledgeMapping
from app.models.ai_analysis import AIAnalysis
from app.models.practice_record import PracticeRecord

__all__ = [
    "User",
    "UserRole",
    "ErrorQuestion",
    "DifficultyLevel",
    "ErrorType",
    "KnowledgePoint",
    "QuestionKnowledgeMapping",
    "AIAnalysis",
    "PracticeRecord",
]

