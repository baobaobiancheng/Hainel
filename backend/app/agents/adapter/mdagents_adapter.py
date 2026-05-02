"""
MDAgents适配器
将MDAgents的同步代码封装为async函数，适配现有BaseAgent接口
"""
import asyncio
from typing import Dict, Any, Optional, List
import threading

from app.agents.base import BaseAgent, AgentContext, AgentResponse
from app.models.conversation import ComplexityLevel
from app.utils.logger import get_logger
from app.ai.llm.base import BaseLLMService

logger = get_logger(__name__)


class MDAgentsAdapter(BaseAgent):
    """MDAgents适配器 - 将MDAgents封装为符合现有接口的异步智能体"""

    def __init__(self, llm_service: Optional[BaseLLMService] = None, model: str = "gpt-4o-mini"):
        """
        初始化MDAgents适配器

        Args:
            llm_service: LLM服务实例
            model: 使用的模型名称
        """
        super().__init__(
            agent_name="MDAgents",
            agent_type="mdagents",
            llm_service=llm_service,
        )
        self.model = model
        self._examplers = []  # 示例数据

    def _run_in_thread(self, func, *args, **kwargs):
        """在线程中运行同步函数"""
        result = None
        exception = None

        def target():
            nonlocal result, exception
            try:
                result = func(*args, **kwargs)
            except Exception as e:
                exception = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join()

        if exception:
            raise exception
        return result

    async def process(
        self,
        context: AgentContext,
        input_data: Dict[str, Any],
    ) -> AgentResponse:
        """
        处理医疗查询 - 主入口

        Args:
            context: 智能体上下文
            input_data: 输入数据（包含chief_complaint等）

        Returns:
            AgentResponse: 响应结果
        """
        self._ensure_initialized()

        # 提取问题
        question = input_data.get("question") or context.chief_complaint
        if not question:
            raise ValueError("问题不能为空")

        # 获取难度/复杂度
        difficulty = input_data.get("difficulty", "adaptive")
        complexity_level = input_data.get("complexity_level")

        # 如果是adaptive模式，使用LLM评估复杂度
        if difficulty == "adaptive" or not difficulty:
            if complexity_level:
                difficulty = self._map_complexity_to_difficulty(complexity_level)
            else:
                difficulty = await self._determine_difficulty_async(question)

        logger.info(f"MDAgents处理问题，难度级别: {difficulty}")

        # 根据难度选择处理方式
        try:
            if difficulty == "basic":
                result = await self._process_basic_async(question)
            elif difficulty == "intermediate":
                result = await self._process_intermediate_async(question)
            elif difficulty == "advanced":
                result = await self._process_advanced_async(question)
            else:
                # 默认使用basic
                result = await self._process_basic_async(question)
        except Exception as e:
            logger.error(f"MDAgents处理出错: {str(e)}")
            result = f"处理出错: {str(e)}"

        # 解析结果
        response_text = self._parse_result(result)
        confidence = self._extract_confidence(result)

        return AgentResponse(
            agent_name=self.agent_name,
            response_text=response_text,
            confidence=confidence,
            structured_data={
                "difficulty": difficulty,
                "model": self.model,
                "raw_result": str(result)[:500],  # 截断以避免过大
            },
            reasoning=f"使用MDAgents {difficulty}模式处理",
            evidence=[],
            metadata={
                "difficulty": difficulty,
                "model": self.model,
            },
        )

    def _map_complexity_to_difficulty(self, complexity_level: str) -> str:
        """将复杂度级别映射到MDAgents难度"""
        if isinstance(complexity_level, ComplexityLevel):
            complexity_level = complexity_level.value

        mapping = {
            "low": "basic",
            "medium": "intermediate",
            "high": "advanced",
        }
        return mapping.get(complexity_level.lower(), "basic")

    async def _determine_difficulty_async(self, question: str) -> str:
        """异步确定难度级别"""
        def sync_determine():
            from app.agents.mdagents.utils import determine_difficulty
            return determine_difficulty(question, "adaptive")

        loop = asyncio.get_event_loop()
        difficulty = await loop.run_in_executor(None, sync_determine)
        return difficulty

    async def _process_basic_async(self, question: str) -> Any:
        """异步处理基础难度问题"""
        def sync_process():
            from app.agents.mdagents.utils import process_basic_query
            return process_basic_query(
                question=question,
                examplers=self._examplers,
                model=self.model,
                args=None
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_process)

    async def _process_intermediate_async(self, question: str) -> Any:
        """异步处理中间难度问题"""
        def sync_process():
            from app.agents.mdagents.utils import process_intermediate_query
            return process_intermediate_query(
                question=question,
                examplers=self._examplers,
                model=self.model,
                args=None
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_process)

    async def _process_advanced_async(self, question: str) -> Any:
        """异步处理高级难度问题"""
        def sync_process():
            from app.agents.mdagents.utils import process_advanced_query
            return process_advanced_query(
                question=question,
                model=self.model,
                args=None
            )

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, sync_process)

    def _parse_result(self, result: Any) -> str:
        """解析结果为文本"""
        if isinstance(result, dict):
            # 处理dict类型结果（如majority vote结果）
            return str(result.get("majority", result))
        elif isinstance(result, dict):
            # 处理响应字典
            return str(result.get("response", result))
        return str(result) if result else "无结果"

    def _extract_confidence(self, result: Any) -> float:
        """提取置信度"""
        # MDAgents不直接返回置信度，使用默认值
        return 0.8

    def get_capabilities(self) -> List[str]:
        """获取智能体能力列表"""
        return [
            "medical_query_processing",
            "adaptive_difficulty",
            "single_agent",
            "multi_expert_discussion",
            "mdt_collaboration",
        ]


# 便捷函数
def create_mdagents_adapter(
    llm_service: Optional[BaseLLMService] = None,
    model: str = "gpt-4o-mini"
) -> MDAgentsAdapter:
    """
    创建MDAgents适配器实例

    Args:
        llm_service: LLM服务
        model: 模型名称

    Returns:
        MDAgentsAdapter实例
    """
    return MDAgentsAdapter(llm_service=llm_service, model=model)


__all__ = ["MDAgentsAdapter", "create_mdagents_adapter"]
