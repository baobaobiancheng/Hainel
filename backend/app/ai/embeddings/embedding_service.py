"""
向量嵌入服务
使用LangChain提供统一的Embedding接口
"""
import os
# 强制离线模式，不尝试联网
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

from typing import List, Optional, Dict, Any
import numpy as np
from langchain_core.embeddings import Embeddings as LangChainEmbeddings
from langchain_community.embeddings import HuggingFaceEmbeddings, OpenAIEmbeddings
from langchain_community.embeddings import DashScopeEmbeddings  # 通义千问

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class EmbeddingService:
    """向量嵌入服务"""
    
    def __init__(
        self,
        model_name: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        **kwargs
    ):
        """
        初始化Embedding服务
        
        Args:
            model_name: 模型名称
            provider: 提供商（openai, huggingface, dashscope）
            api_key: API密钥
            **kwargs: 其他参数
        """
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.provider = provider or self._detect_provider()
        self.api_key = api_key
        self.kwargs = kwargs
        self._embeddings: Optional[LangChainEmbeddings] = None
        self._initialized = False
    
    def _detect_provider(self) -> str:
        """自动检测提供商"""
        model_name = self.model_name.lower()

        # 通义千问 DashScope embedding：text-embedding-v1/v2/v3
        if "text-embedding-v" in model_name or "dashscope" in model_name or "qwen" in model_name:
            return "dashscope"
        # OpenAI embedding：text-embedding-ada-002 / text-embedding-3-*
        elif "ada" in model_name or "text-embedding-3" in model_name:
            return "openai"
        else:
            return "huggingface"
    
    def _initialize(self):
        """初始化Embedding引擎"""
        try:
            logger.info(f"正在初始化Embedding服务: {self.model_name} (provider={self.provider})")
            
            if self.provider == "openai":
                self._embeddings = OpenAIEmbeddings(
                    model=self.model_name,
                    openai_api_key=self.api_key or settings.LLM_API_KEY,
                    **self.kwargs
                )
            elif self.provider == "dashscope":
                # 使用通义千问的Embedding
                self._embeddings = DashScopeEmbeddings(
                    model=self.model_name,
                    dashscope_api_key=self.api_key or settings.LLM_API_KEY,
                    **self.kwargs
                )
            else:
                # 使用HuggingFace Embeddings - 本地离线模型
                self._embeddings = HuggingFaceEmbeddings(
                    model_name=self.model_name,
                    model_kwargs={"device": "cpu", "local_files_only": True},
                    encode_kwargs={"normalize_embeddings": True},
                    cache_folder=getattr(settings, 'CHROMA_MODEL_CACHE_DIR', None),
                )
            
            logger.info("Embedding服务初始化成功")
            self._initialized = True
        except Exception as e:
            logger.error(f"Embedding初始化失败: {e}", exc_info=True)
            raise
    
    def _ensure_initialized(self):
        """确保Embedding已初始化"""
        if not self._initialized or self._embeddings is None:
            self._initialize()
    
    def embed_query(self, text: str) -> List[float]:
        """
        嵌入单个查询文本
        
        Args:
            text: 文本内容
            
        Returns:
            List[float]: 嵌入向量
        """
        self._ensure_initialized()
        
        try:
            return self._embeddings.embed_query(text)
        except Exception as e:
            logger.error(f"文本嵌入失败: {e}", exc_info=True)
            raise
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        嵌入文档列表
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        self._ensure_initialized()
        
        try:
            return self._embeddings.embed_documents(texts)
        except Exception as e:
            logger.error(f"文档嵌入失败: {e}", exc_info=True)
            raise
    
    async def aembed_query(self, text: str) -> List[float]:
        """
        异步嵌入单个查询文本
        
        Args:
            text: 文本内容
            
        Returns:
            List[float]: 嵌入向量
        """
        self._ensure_initialized()
        
        try:
            if hasattr(self._embeddings, 'aembed_query'):
                return await self._embeddings.aembed_query(text)
            else:
                # 如果不支持异步，使用同步方法
                return self.embed_query(text)
        except Exception as e:
            logger.error(f"异步文本嵌入失败: {e}", exc_info=True)
            raise
    
    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        异步嵌入文档列表
        
        Args:
            texts: 文本列表
            
        Returns:
            List[List[float]]: 嵌入向量列表
        """
        self._ensure_initialized()
        
        try:
            if hasattr(self._embeddings, 'aembed_documents'):
                return await self._embeddings.aembed_documents(texts)
            else:
                # 如果不支持异步，使用同步方法
                return self.embed_documents(texts)
        except Exception as e:
            logger.error(f"异步文档嵌入失败: {e}", exc_info=True)
            raise
    
    def get_embedding_dimension(self) -> int:
        """获取嵌入向量维度"""
        name = self.model_name.lower()
        if "text-embedding-v" in name:          # 通义千问 v1/v2/v3 均为 1536
            return 1536
        elif "ada-002" in name:
            return 1536
        elif "text-embedding-3" in name:
            return 1536
        else:
            return settings.EMBEDDING_DIMENSION
    
    def cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """
        计算两个向量的余弦相似度
        
        Args:
            vec1: 向量1
            vec2: 向量2
            
        Returns:
            float: 余弦相似度（-1到1）
        """
        vec1_array = np.array(vec1)
        vec2_array = np.array(vec2)
        
        dot_product = np.dot(vec1_array, vec2_array)
        norm1 = np.linalg.norm(vec1_array)
        norm2 = np.linalg.norm(vec2_array)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "model_name": self.model_name,
            "provider": self.provider,
            "dimension": self.get_embedding_dimension(),
            "initialized": self._initialized,
        }


# 创建默认的Embedding服务实例
_default_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service(
    model_name: Optional[str] = None,
    provider: Optional[str] = None,
    api_key: Optional[str] = None,
    **kwargs
) -> EmbeddingService:
    """
    获取Embedding服务实例（单例模式）
    
    Args:
        model_name: 模型名称
        provider: 提供商
        api_key: API密钥
        **kwargs: 其他参数
        
    Returns:
        EmbeddingService: Embedding服务实例
    """
    global _default_embedding_service
    
    if _default_embedding_service is None:
        _default_embedding_service = EmbeddingService(
            model_name=model_name,
            provider=provider,
            api_key=api_key,
            **kwargs
        )
    
    return _default_embedding_service

