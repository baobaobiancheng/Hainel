"""
智能体基础设施模块
提供智能体基类、接口和消息格式定义
"""
from app.agents.base.agent_base import BaseAgent
from app.agents.base.agent_interface import AgentInterface, AgentContext, AgentResponse
from app.agents.base.message import (
    MessageType,
    AgentMessage,
    DiscussionMessage,
    ConsensusResult,
    AgentResponse as MessageAgentResponse,
)

__all__ = [
    "BaseAgent",
    "AgentInterface",
    "AgentContext",
    "AgentResponse",
    "MessageType",
    "AgentMessage",
    "DiscussionMessage",
    "ConsensusResult",
    "MessageAgentResponse",
]

