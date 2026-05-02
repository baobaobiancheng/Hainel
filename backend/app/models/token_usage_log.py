from sqlalchemy import Boolean, Column, Integer, String

from app.models.base import BaseModel


class TokenUsageLog(BaseModel):
    provider = Column(String(50), nullable=False, index=True, comment="模型提供商")
    model_name = Column(String(255), nullable=False, index=True, comment="模型名称")
    source_type = Column(String(100), nullable=False, index=True, comment="调用来源")
    prompt_tokens = Column(Integer, nullable=False, default=0, comment="输入 token")
    completion_tokens = Column(Integer, nullable=False, default=0, comment="输出 token")
    total_tokens = Column(Integer, nullable=False, default=0, comment="总 token")
    success = Column(Boolean, nullable=False, default=True, comment="调用是否成功")


__all__ = ["TokenUsageLog"]
