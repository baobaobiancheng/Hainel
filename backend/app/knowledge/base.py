"""
知识库基类
提供统一的知识库接口
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.utils.logger import get_logger

logger = get_logger(__name__)


class KnowledgeItem(BaseModel):
    """知识条目"""
    id: str = Field(description="知识ID")
    title: str = Field(description="标题")
    content: str = Field(description="内容")
    category: Optional[str] = Field(default=None, description="分类")
    tags: List[str] = Field(default_factory=list, description="标签")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class SearchResult(BaseModel):
    """搜索结果"""
    items: List[KnowledgeItem] = Field(description="知识条目列表")
    total: int = Field(description="总数")
    query: str = Field(description="查询文本")


class BaseKnowledgeBase(ABC):
    """知识库基类"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        初始化知识库
        
        Args:
            config: 配置字典
        """
        self.config = config or {}
        self._initialized = False
    
    @abstractmethod
    def _initialize(self):
        """初始化知识库"""
        pass
    
    def _ensure_initialized(self):
        """确保知识库已初始化"""
        if not self._initialized:
            self._initialize()
            self._initialized = True
    
    @abstractmethod
    def search(
        self,
        query: str,
        top_k: int = 5,
        **kwargs
    ) -> SearchResult:
        """
        搜索知识库
        
        Args:
            query: 查询文本
            top_k: 返回前k个结果
            **kwargs: 其他参数
            
        Returns:
            SearchResult: 搜索结果
        """
        pass
    
    @abstractmethod
    def get_by_id(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """
        根据ID获取知识条目
        
        Args:
            knowledge_id: 知识ID
            
        Returns:
            KnowledgeItem: 知识条目，如果不存在返回None
        """
        pass
    
    @abstractmethod
    def add(self, item: KnowledgeItem) -> bool:
        """
        添加知识条目
        
        Args:
            item: 知识条目
            
        Returns:
            bool: 是否成功
        """
        pass
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "service_type": self.__class__.__name__,
            "initialized": self._initialized,
        }

