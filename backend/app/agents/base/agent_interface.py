"""
智能体接口定义
定义智能体的统一接口规范
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
from pydantic import BaseModel

from app.agents.base.message import AgentMessage, AgentResponse


class AgentContext(BaseModel):
    """智能体上下文"""
    conversation_id: int
    patient_id: int
    chief_complaint: Optional[str] = None
    medical_history: Optional[Dict[str, Any]] = None
    examination_results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None


class AgentInterface(ABC):
    """智能体接口"""
    
    @property
    @abstractmethod
    def agent_name(self) -> str:
        """智能体名称"""
        pass
    
    @property
    @abstractmethod
    def agent_type(self) -> str:
        """智能体类型"""
        pass
    
    @abstractmethod
    async def process(
        self,
        context: AgentContext,
        input_data: Dict[str, Any],
    ) -> AgentResponse:
        """
        处理请求（主要接口）
        
        Args:
            context: 智能体上下文
            input_data: 输入数据
            
        Returns:
            AgentResponse: 智能体响应
        """
        pass
    
    @abstractmethod
    async def respond(
        self,
        message: AgentMessage,
    ) -> Optional[AgentMessage]:
        """
        响应消息（用于智能体间通信）
        
        Args:
            message: 接收到的消息
            
        Returns:
            Optional[AgentMessage]: 响应消息（如果不需要响应则返回None）
        """
        pass
    
    async def evaluate(
        self,
        context: AgentContext,
        response: AgentResponse,
    ) -> Dict[str, Any]:
        """
        评估响应质量（可选）
        
        Args:
            context: 智能体上下文
            response: 智能体响应
            
        Returns:
            Dict[str, Any]: 评估结果
        """
        return {}
    
    def get_capabilities(self) -> List[str]:
        """
        获取智能体能力列表
        
        Returns:
            List[str]: 能力列表
        """
        return []
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        获取智能体元数据
        
        Returns:
            Dict[str, Any]: 元数据
        """
        return {
            "agent_name": self.agent_name,
            "agent_type": self.agent_type,
            "capabilities": self.get_capabilities(),
        }

