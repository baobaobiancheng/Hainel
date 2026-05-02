"""
智能体基类
所有智能体的抽象基类，提供通用功能
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
import uuid

from app.ai.llm.base import BaseLLMService
from app.agents.base.agent_interface import AgentInterface, AgentContext, AgentResponse
from app.agents.base.message import AgentMessage, MessageType
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BaseAgent(AgentInterface):
    """智能体基类"""
    
    def __init__(
        self,
        agent_name: str,
        agent_type: str,
        llm_service: Optional[BaseLLMService] = None,
    ):
        """
        初始化智能体
        
        Args:
            agent_name: 智能体名称
            agent_type: 智能体类型
            llm_service: LLM服务实例
        """
        self._agent_name = agent_name
        self._agent_type = agent_type
        self._llm_service = llm_service
        self._initialized = False
    
    @property
    def agent_name(self) -> str:
        """智能体名称"""
        return self._agent_name
    
    @property
    def agent_type(self) -> str:
        """智能体类型"""
        return self._agent_type
    
    @property
    def llm_service(self) -> Optional[BaseLLMService]:
        """LLM服务"""
        return self._llm_service
    
    def _ensure_initialized(self):
        """确保智能体已初始化"""
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    def _initialize(self):
        """初始化智能体（子类可重写）"""
        pass
    
    async def process(
        self,
        context: AgentContext,
        input_data: Dict[str, Any],
    ) -> AgentResponse:
        """
        处理请求（默认实现，子类应重写）
        
        Args:
            context: 智能体上下文
            input_data: 输入数据
            
        Returns:
            AgentResponse: 智能体响应
        """
        self._ensure_initialized()
        
        # 默认实现：使用LLM生成响应
        if self._llm_service:
            prompt = self._build_prompt(context, input_data)
            system_prompt = self._build_system_prompt(context)
            
            try:
                llm_response = await self._llm_service.agenerate(
                    prompt=prompt,
                    system_prompt=system_prompt,
                )
                
                return AgentResponse(
                    agent_name=self.agent_name,
                    response_text=llm_response.content,
                    confidence=0.7,  # 默认置信度
                    structured_data=None,
                    reasoning=None,
                    evidence=[],
                    metadata={"model": llm_response.model},
                )
            except Exception as e:
                logger.error(f"智能体 {self.agent_name} 处理失败: {e}", exc_info=True)
                raise
        
        # 如果没有LLM服务，返回默认响应
        return AgentResponse(
            agent_name=self.agent_name,
            response_text="智能体未配置LLM服务",
            confidence=0.0,
            structured_data=None,
            reasoning=None,
            evidence=[],
            metadata={},
        )
    
    async def respond(
        self,
        message: AgentMessage,
    ) -> Optional[AgentMessage]:
        """
        响应消息（默认实现，子类可重写）
        
        Args:
            message: 接收到的消息
            
        Returns:
            Optional[AgentMessage]: 响应消息
        """
        self._ensure_initialized()
        
        # 默认实现：不响应
        return None
    
    def _build_system_prompt(self, context: AgentContext) -> str:
        """
        构建系统提示（子类可重写）
        
        Args:
            context: 智能体上下文
            
        Returns:
            str: 系统提示
        """
        return f"你是一个专业的{self.agent_type}智能体，名称为{self.agent_name}。"
    
    def _build_prompt(
        self,
        context: AgentContext,
        input_data: Dict[str, Any],
    ) -> str:
        """
        构建用户提示（子类可重写）
        
        Args:
            context: 智能体上下文
            input_data: 输入数据
            
        Returns:
            str: 用户提示
        """
        prompt_parts = []
        
        if context.chief_complaint:
            prompt_parts.append(f"患者主诉：{context.chief_complaint}")
        
        if input_data.get("query"):
            prompt_parts.append(f"查询：{input_data['query']}")
        
        return "\n".join(prompt_parts) if prompt_parts else "请处理这个请求。"
    
    def _create_message(
        self,
        conversation_id: int,
        receiver: Optional[str],
        message_type: MessageType,
        content: str,
        structured_data: Optional[Dict[str, Any]] = None,
        confidence: Optional[float] = None,
        **kwargs
    ) -> AgentMessage:
        """
        创建消息
        
        Args:
            conversation_id: 会话ID
            receiver: 接收者
            message_type: 消息类型
            content: 消息内容
            structured_data: 结构化数据
            confidence: 置信度
            **kwargs: 其他参数
            
        Returns:
            AgentMessage: 消息对象
        """
        return AgentMessage(
            message_id=str(uuid.uuid4()),
            conversation_id=conversation_id,
            sender=self.agent_name,
            receiver=receiver,
            message_type=message_type,
            content=content,
            structured_data=structured_data,
            confidence=confidence,
            timestamp=datetime.utcnow(),
            metadata=kwargs,
        )
    
    def get_capabilities(self) -> List[str]:
        """获取智能体能力列表"""
        return ["process", "respond"]
    
    def __repr__(self) -> str:
        """返回智能体的字符串表示"""
        return f"<{self.__class__.__name__}(name={self.agent_name}, type={self.agent_type})>"


# 导出
__all__ = ["BaseAgent"]

