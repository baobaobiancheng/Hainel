"""
AI模型服务层
"""
from app.ai.llm.base import BaseLLMService, LLMResponse, LLMConfig
from app.ai.llm.qwen import QwenLLMService, QwenLocalLLMService, get_qwen_service
from app.ai.ocr.base import BaseOCRService, OCRResult
from app.ai.embeddings.embedding_service import EmbeddingService, get_embedding_service

__all__ = [
    # LLM
    "BaseLLMService",
    "LLMResponse",
    "LLMConfig",
    "QwenLLMService",
    "QwenLocalLLMService",
    "get_qwen_service",
    # OCR
    "BaseOCRService",
    "OCRResult",
    # Embeddings
    "EmbeddingService",
    "get_embedding_service",
]

