"""
智能体消息格式定义
定义智能体间通信的消息格式
"""
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """消息类型枚举"""
    ANALYSIS = "analysis"  # 分析
    QUESTION = "question"  # 问题
    ANSWER = "answer"  # 回答
    CONSENSUS = "consensus"  # 共识
    REPORT = "report"  # 报告
    REQUEST = "request"  # 请求
    RESPONSE = "response"  # 响应
    NOTIFICATION = "notification"  # 通知


class AgentMessage(BaseModel):
    """智能体消息模型"""
    
    # 消息标识
    message_id: str = Field(..., description="消息ID")
    conversation_id: int = Field(..., description="会话ID")
    session_id: Optional[str] = Field(None, description="会话会话ID")
    
    # 发送者和接收者
    sender: str = Field(..., description="发送者（智能体名称）")
    receiver: Optional[str] = Field(None, description="接收者（智能体名称，None表示广播）")
    
    # 消息类型和内容
    message_type: MessageType = Field(..., description="消息类型")
    content: str = Field(..., description="消息文本内容")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="结构化数据")
    
    # 置信度和证据
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0, description="置信度（0-1）")
    evidence: Optional[List[str]] = Field(None, description="证据列表")
    
    # 元数据
    complexity_level: Optional[str] = Field(None, description="复杂度级别")
    discussion_round: Optional[int] = Field(None, description="讨论轮次")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(None, description="扩展元数据")
    
    class Config:
        use_enum_values = True


class DiscussionMessage(BaseModel):
    """讨论消息模型（用于MDT/ICT模式）"""
    
    agent_name: str = Field(..., description="智能体名称")
    round_number: int = Field(..., description="讨论轮次")
    opinion: str = Field(..., description="观点/分析")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    evidence: List[str] = Field(default_factory=list, description="证据列表")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="结构化数据")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="时间戳")


class ConsensusResult(BaseModel):
    """共识结果模型"""
    
    achieved: bool = Field(..., description="是否达成共识")
    consensus_rate: float = Field(..., ge=0.0, le=1.0, description="共识率")
    consensus_opinion: Optional[str] = Field(None, description="共识观点")
    participant_count: int = Field(..., description="参与者数量")
    agreement_count: int = Field(..., description="同意数量")
    discussion_rounds: int = Field(..., description="讨论轮次")
    details: Optional[Dict[str, Any]] = Field(None, description="详细信息")


class AgentResponse(BaseModel):
    """智能体响应模型"""
    
    agent_name: str = Field(..., description="智能体名称")
    response_text: str = Field(..., description="响应文本")
    confidence: float = Field(..., ge=0.0, le=1.0, description="置信度")
    structured_data: Optional[Dict[str, Any]] = Field(None, description="结构化数据")
    reasoning: Optional[str] = Field(None, description="推理过程")
    evidence: List[str] = Field(default_factory=list, description="证据列表")
    metadata: Optional[Dict[str, Any]] = Field(None, description="元数据")


# 导出
__all__ = [
    "MessageType",
    "AgentMessage",
    "DiscussionMessage",
    "ConsensusResult",
    "AgentResponse",
]

