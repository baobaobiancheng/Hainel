"""
多智能体系统模块
基于MDAgents框架的自适应多智能体协作系统
"""
# 基础模块
from app.agents.base import (
    BaseAgent,
    AgentInterface,
    AgentContext,
    AgentResponse,
    MessageType,
    AgentMessage,
)

# MDAgents适配器
from app.agents.adapter import (
    MDAgentsAdapter,
    create_mdagents_adapter,
)

__all__ = [
    # 基础
    "BaseAgent",
    "AgentInterface",
    "AgentContext",
    "AgentResponse",
    "MessageType",
    "AgentMessage",
    # MDAgents适配器
    "MDAgentsAdapter",
    "create_mdagents_adapter",
]
