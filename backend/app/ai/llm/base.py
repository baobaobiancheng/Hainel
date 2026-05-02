"""
LLM base classes and shared response helpers.
"""
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.token_usage_service import token_usage_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class LLMResponse(BaseModel):
    content: str = Field(description="响应内容")
    model: str = Field(description="模型名称")
    usage: Optional[Dict[str, int]] = Field(default=None, description="Token 使用情况")
    finish_reason: Optional[str] = Field(default=None, description="结束原因")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="附加元数据")


class LLMConfig(BaseModel):
    model_name: str = Field(description="模型名称")
    temperature: float = Field(default=0.7, description="温度")
    max_tokens: int = Field(default=2048, description="最大 token")
    timeout: int = Field(default=60, description="超时时间")
    api_key: Optional[str] = Field(default=None, description="API Key")
    api_base: Optional[str] = Field(default=None, description="API Base URL")
    extra_params: Optional[Dict[str, Any]] = Field(default=None, description="额外参数")


class BaseLLMService(ABC):
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or self._get_default_config()
        self._llm: Optional[BaseChatModel] = None
        self._initialized = False

    @abstractmethod
    def _get_default_config(self) -> LLMConfig:
        pass

    @abstractmethod
    def _create_llm(self) -> BaseChatModel:
        pass

    def _ensure_initialized(self) -> None:
        if not self._initialized or self._llm is None:
            self._llm = self._create_llm()
            self._initialized = True
            logger.info(f"LLM service initialized: {self.config.model_name}")

    def _extract_usage(self, response: Any) -> Optional[Dict[str, int]]:
        if hasattr(response, "response_metadata"):
            return response.response_metadata.get("token_usage", {})
        return None

    def _record_usage(self, usage: Optional[Dict[str, int]], source_type: str) -> None:
        provider = self.__class__.__name__.replace("LLMService", "").replace("Local", "").lower() or "llm"
        token_usage_service.record_usage(
            provider=provider,
            model_name=self.config.model_name,
            source_type=source_type,
            usage=usage,
            success=True,
        )

    def _to_response(self, response: Any, usage: Optional[Dict[str, int]]) -> LLMResponse:
        content = response.content if hasattr(response, "content") else str(response)
        return LLMResponse(
            content=content,
            model=self.config.model_name,
            usage=usage,
            finish_reason=None,
            metadata={"response_metadata": getattr(response, "response_metadata", {})},
        )

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        **kwargs,
    ) -> LLMResponse:
        self._ensure_initialized()

        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        params = {
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **kwargs,
        }

        try:
            response = self._llm.invoke(messages, callbacks=callbacks, **params)
            usage = self._extract_usage(response)
            self._record_usage(usage, "llm_generate")
            return self._to_response(response, usage)
        except Exception as exc:
            logger.error(f"LLM 生成失败: {exc}", exc_info=True)
            raise

    async def agenerate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        **kwargs,
    ) -> LLMResponse:
        self._ensure_initialized()

        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        params = {
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **kwargs,
        }

        try:
            response = await self._llm.ainvoke(messages, callbacks=callbacks, **params)
            usage = self._extract_usage(response)
            self._record_usage(usage, "llm_agenerate")
            return self._to_response(response, usage)
        except Exception as exc:
            logger.error(f"LLM 异步生成失败: {exc}", exc_info=True)
            raise

    async def astream(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        self._ensure_initialized()

        messages: List[BaseMessage] = []
        if system_prompt:
            messages.append(SystemMessage(content=system_prompt))
        messages.append(HumanMessage(content=prompt))

        params = {
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **kwargs,
        }

        try:
            async for chunk in self._llm.astream(messages, callbacks=callbacks, **params):
                yield chunk.content if hasattr(chunk, "content") else str(chunk)
        except Exception as exc:
            logger.error(f"LLM 流式生成失败: {exc}", exc_info=True)
            raise

    def chat(
        self,
        messages: List[BaseMessage],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        callbacks: Optional[List[BaseCallbackHandler]] = None,
        **kwargs,
    ) -> LLMResponse:
        self._ensure_initialized()

        params = {
            "temperature": temperature or self.config.temperature,
            "max_tokens": max_tokens or self.config.max_tokens,
            **kwargs,
        }

        try:
            response = self._llm.invoke(messages, callbacks=callbacks, **params)
            usage = self._extract_usage(response)
            self._record_usage(usage, "llm_chat")
            return self._to_response(response, usage)
        except Exception as exc:
            logger.error(f"LLM 对话失败: {exc}", exc_info=True)
            raise

    def get_model_info(self) -> Dict[str, Any]:
        return {
            "model_name": self.config.model_name,
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
            "timeout": self.config.timeout,
        }
