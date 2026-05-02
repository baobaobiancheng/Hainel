"""
适配器模块
提供不同框架之间的适配层
"""
from app.agents.adapter.mdagents_adapter import (
    MDAgentsAdapter,
    create_mdagents_adapter,
)

__all__ = [
    "MDAgentsAdapter",
    "create_mdagents_adapter",
]
