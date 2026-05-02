"""
Milvus Lite 知识库搜索模块

使用 Milvus Lite（本地文件，无需独立服务进程）实现语义向量搜索。
Embedding 使用通义千问 text-embedding-v2（DashScope）。

数据库文件路径由 settings.MILVUS_URI 配置，默认 data/milvus.db。
"""
import os
from typing import List, Dict, Any, Optional

from langchain_community.vectorstores import Milvus
from langchain_core.documents import Document

from app.ai.embeddings.embedding_service import get_embedding_service
from app.knowledge.base import BaseKnowledgeBase, KnowledgeItem, SearchResult
from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MilvusLiteKnowledgeBase(BaseKnowledgeBase):
    """基于 Milvus Lite 的本地向量知识库"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.milvus_uri: str = self.config.get("milvus_uri", settings.MILVUS_URI)
        self.collection_name: str = self.config.get(
            "collection_name", settings.MILVUS_COLLECTION_NAME
        )
        self._embedding_service = None
        self._vector_store: Optional[Milvus] = None

    # ------------------------------------------------------------------
    # 内部初始化
    # ------------------------------------------------------------------

    def _initialize(self):
        """初始化 Milvus Lite 向量库"""
        try:
            logger.info("正在初始化 Milvus Lite 知识库")

            # 确保数据库目录存在
            db_dir = os.path.dirname(self.milvus_uri)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

            # Bug 1 修复：先调用 _ensure_initialized()，再访问 _embeddings
            self._embedding_service = get_embedding_service()
            self._embedding_service._ensure_initialized()
            embeddings = self._embedding_service._embeddings  # 此时保证非 None

            # 连接 Milvus Lite（uri 为本地文件路径，无需独立服务）
            # drop_old=False：若集合已存在则复用，不清空数据
            self._vector_store = Milvus(
                embedding_function=embeddings,
                collection_name=self.collection_name,
                connection_args={"uri": self.milvus_uri},
                auto_id=True,
                enable_dynamic_field=True,
                drop_old=False,
            )

            logger.info(
                f"Milvus Lite 知识库初始化成功 [uri={self.milvus_uri}, "
                f"collection={self.collection_name}]"
            )
        except Exception as e:
            logger.error(f"Milvus Lite 知识库初始化失败: {e}", exc_info=True)
            raise

    # ------------------------------------------------------------------
    # 核心接口
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5, **kwargs) -> SearchResult:
        """
        向量语义搜索

        Args:
            query:  查询文本（自然语言）
            top_k:  返回结果数量
            expr:   可选的 Milvus 过滤表达式，如 'category == "内科"'

        Returns:
            SearchResult
        """
        self._ensure_initialized()
        try:
            expr: Optional[str] = kwargs.get("expr")
            docs_with_scores = self._vector_store.similarity_search_with_score(
                query, k=top_k, expr=expr
            )
            items: List[KnowledgeItem] = []
            for doc, score in docs_with_scores:
                meta = doc.metadata
                items.append(
                    KnowledgeItem(
                        id=meta.get("item_id", ""),
                        title=meta.get("title", doc.page_content[:50]),
                        content=doc.page_content,
                        category=meta.get("category"),
                        tags=meta.get("tags") or [],
                        metadata={**meta, "score": float(score)},
                    )
                )
            return SearchResult(items=items, total=len(items), query=query)
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}", exc_info=True)
            raise

    def get_by_id(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """
        根据 item_id 精确查找知识条目。

        使用 Milvus 表达式过滤（不做向量相似度计算），正确实现 ID 查询。
        """
        self._ensure_initialized()
        try:
            # expr 过滤动态字段 item_id，k=1 避免多余结果
            results = self._vector_store.similarity_search(
                query=knowledge_id,
                k=1,
                expr=f'item_id == "{knowledge_id}"',
            )
            if not results:
                return None
            doc = results[0]
            meta = doc.metadata
            return KnowledgeItem(
                id=meta.get("item_id", knowledge_id),
                title=meta.get("title", ""),
                content=doc.page_content,
                category=meta.get("category"),
                tags=meta.get("tags") or [],
                metadata=meta,
            )
        except Exception as e:
            logger.error(f"获取知识条目失败 [id={knowledge_id}]: {e}", exc_info=True)
            return None

    def add(self, item: KnowledgeItem) -> bool:
        """
        添加单条知识条目。

        每条 KnowledgeItem 存为一个 Document（不做文本分块），
        item_id 作为可过滤的动态字段，避免 Milvus 内置 id 字段冲突。
        """
        self._ensure_initialized()
        try:
            doc = Document(
                page_content=item.content,
                metadata={
                    "item_id": item.id,
                    "title": item.title,
                    "category": item.category or "",
                    "tags": item.tags,
                    # 过滤掉 score 字段，避免写入无意义的临时数据
                    **{k: v for k, v in item.metadata.items() if k != "score"},
                },
            )
            self._vector_store.add_documents([doc])
            logger.info(f"成功添加知识条目: {item.id}")
            return True
        except Exception as e:
            logger.error(f"添加知识条目失败 [id={item.id}]: {e}", exc_info=True)
            return False

    def add_batch(self, items: List[KnowledgeItem]) -> bool:
        """
        批量添加知识条目。

        Bug 修复：统一构建所有 Document 后一次性调用 add_documents，
        避免原来逐条 add() 导致的重复写入开销。
        """
        self._ensure_initialized()
        if not items:
            return True
        try:
            documents = [
                Document(
                    page_content=item.content,
                    metadata={
                        "item_id": item.id,
                        "title": item.title,
                        "category": item.category or "",
                        "tags": item.tags,
                        **{k: v for k, v in item.metadata.items() if k != "score"},
                    },
                )
                for item in items
            ]
            self._vector_store.add_documents(documents)
            logger.info(f"成功批量添加 {len(items)} 条知识条目")
            return True
        except Exception as e:
            logger.error(f"批量添加知识条目失败: {e}", exc_info=True)
            return False


# ------------------------------------------------------------------
# 单例工厂
# ------------------------------------------------------------------

_default_knowledge_base: Optional[MilvusLiteKnowledgeBase] = None


def get_knowledge_base(config: Optional[Dict[str, Any]] = None) -> MilvusLiteKnowledgeBase:
    """
    获取 Milvus Lite 知识库单例。

    首次调用时创建实例；向量库的实际初始化（连接 DB + 初始化 Embedding）
    延迟到第一次调用 search/add 时触发（lazy init）。
    """
    global _default_knowledge_base
    if _default_knowledge_base is None:
        _default_knowledge_base = MilvusLiteKnowledgeBase(config=config)
    return _default_knowledge_base


__all__ = ["MilvusLiteKnowledgeBase", "get_knowledge_base"]
