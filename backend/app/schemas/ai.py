"""
AI 分析相关 Schema
"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class AIAnalysisRequest(BaseModel):
    """AI 分析请求"""
    question_id: str = Field(..., description="错题ID")
    analysis_types: List[str] = Field(
        default=["error_analysis"],
        description="分析类型列表: error_analysis, similar_questions, explanation, knowledge_extraction"
    )


class ErrorAnalysisResult(BaseModel):
    """错误分析结果"""
    error_reason: str = Field(..., description="错误原因")
    error_category: str = Field(..., description="错误类别")
    knowledge_gaps: List[str] = Field(default=[], description="知识漏洞")
    suggestions: List[str] = Field(default=[], description="改进建议")


class SimilarQuestion(BaseModel):
    """相似题目"""
    question_text: str
    similarity_score: float
    source: Optional[str] = None


class SimilarQuestionsResult(BaseModel):
    """相似题推荐结果"""
    similar_questions: List[SimilarQuestion]
    total_count: int


class ExplanationResult(BaseModel):
    """解题思路结果"""
    step_by_step: List[str] = Field(..., description="逐步解析")
    key_points: List[str] = Field(default=[], description="关键点")
    alternative_methods: List[str] = Field(default=[], description="替代方法")


class KnowledgePoint(BaseModel):
    """知识点"""
    name: str
    relevance: float  # 0-1


class KnowledgeExtractionResult(BaseModel):
    """知识点提取结果"""
    knowledge_points: List[KnowledgePoint]


class AIAnalysisResponse(BaseModel):
    """AI 分析响应"""
    analysis_id: str
    question_id: str
    analysis_type: str
    result: Dict[str, Any]
    model_name: Optional[str] = None
    tokens_used: Optional[int] = None
    created_at: str

