"""
Chroma 本地向量知识库模块

使用 Chroma 作为向量数据库，EmbeddingService 进行本地离线嵌入。

特点：
- 纯本地运行，无需外部服务
- 使用已有的 EmbeddingService（支持 bge-small-zh-v1.5 等本地模型）
- 搜索时只对查询进行嵌入召回，不重新嵌入文档
"""
import os
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

import chromadb
from typing import List, Dict, Any, Optional

from llama_index.core import (
    SimpleDirectoryReader,
    Document,
    StorageContext,
)

from app.knowledge.base import BaseKnowledgeBase, KnowledgeItem, SearchResult
from app.config import settings
from app.ai.embeddings.embedding_service import get_embedding_service
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ChromaKnowledgeBase(BaseKnowledgeBase):
    """基于 Chroma + LlamaIndex 的本地向量知识库"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        # 配置项
        self.collection_name: str = self.config.get(
            "collection_name", settings.CHROMA_COLLECTION_NAME
        )
        self.persist_dir: str = self.config.get(
            "persist_dir", settings.CHROMA_PERSIST_DIR
        )
        self.embedding_model: str = self.config.get(
            "embedding_model", settings.CHROMA_EMBEDDING_MODEL
        )
        self.chunk_size: int = self.config.get("chunk_size", 512)
        self.chunk_overlap: int = self.config.get("chunk_overlap", 50)

        self._embedding_service = None
        self._chroma_client = None
        self._collection = None
        self._initialized = False

    # ------------------------------------------------------------------
    # 内部初始化
    # ------------------------------------------------------------------

    def _initialize(self):
        """初始化 Chroma 向量库和 Embedding 模型"""
        try:
            logger.info(f"正在初始化 Chroma 知识库: {self.persist_dir}")

            # 确保目录存在
            os.makedirs(self.persist_dir, exist_ok=True)

            # 使用已有的 EmbeddingService（本地离线模型）
            logger.info(f"正在加载本地 Embedding 服务: {self.embedding_model}")
            self._embedding_service = get_embedding_service(
                model_name=self.embedding_model,
                provider="huggingface"
            )

            # 初始化 Chroma 客户端（不使用 embedding_function，数据已预嵌入）
            self._chroma_client = chromadb.PersistentClient(path=self.persist_dir)
            self._collection = self._chroma_client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
            )

            logger.info(
                f"Chroma 知识库初始化成功 [collection={self.collection_name}, "
                f"persist_dir={self.persist_dir}, embedding={self.embedding_model}]"
            )
            self._initialized = True
        except Exception as e:
            logger.error(f"Chroma 知识库初始化失败: {e}", exc_info=True)
            raise

    def _ensure_initialized(self):
        """确保知识库已初始化"""
        if not self._initialized or self._collection is None:
            self._initialize()

    # ------------------------------------------------------------------
    # 文档导入接口
    # ------------------------------------------------------------------

    def ingest_directory(
        self,
        directory: str,
        recursive: bool = True,
        file_types: Optional[List[str]] = None,
    ) -> int:
        """
        从目录批量导入文档

        Args:
            directory: 文档目录路径
            recursive: 是否递归扫描子目录
            file_types: 允许的文件扩展名，如 ["pdf", "docx", "txt"]

        Returns:
            导入的文档数量
        """
        self._ensure_initialized()

        if file_types is None:
            file_types = ["pdf", "docx", "doc", "xlsx", "xls", "txt", "md", "html"]

        try:
            logger.info(f"正在从目录导入文档: {directory}")

            # 使用 SimpleDirectoryReader 加载文档
            reader = SimpleDirectoryReader(
                input_dir=directory,
                recursive=recursive,
                file_metadata_fn=self._get_file_metadata,
            )

            # 只加载指定类型的文件
            files_to_load = []
            for root, _, files in os.walk(directory):
                for f in files:
                    ext = f.split(".")[-1].lower() if "." in f else ""
                    if ext in file_types:
                        files_to_load.append(os.path.join(root, f))

            if not files_to_load:
                logger.warning(f"目录 {directory} 中没有找到匹配的文件类型")
                return 0

            # 手动加载文件
            documents = []
            for file_path in files_to_load:
                try:
                    doc = self._load_single_file(file_path)
                    if doc:
                        documents.append(doc)
                except Exception as e:
                    logger.warning(f"加载文件失败 {file_path}: {e}")

            if documents:
                # 解析文档并添加到索引
                self._index.insert_nodes(
                    self._index.node_store.get_nodes(
                        [self._index.docstore.add_documents(documents)]
                    )
                )
                # 使用更简单的方式添加文档
                from llama_index.core import VectorStoreIndex
                index = VectorStoreIndex.from_documents(
                    documents,
                    storage_context=StorageContext.from_defaults(
                        vector_store=self._vector_store
                    ),
                )
                logger.info(f"成功导入 {len(documents)} 个文档")
                return len(documents)
            return 0
        except Exception as e:
            logger.error(f"批量导入文档失败: {e}", exc_info=True)
            raise

    def ingest_file(self, file_path: str) -> bool:
        """
        导入单个文档文件

        Args:
            file_path: 文件路径

        Returns:
            是否成功
        """
        self._ensure_initialized()

        try:
            logger.info(f"正在导入文档: {file_path}")
            doc = self._load_single_file(file_path)
            if doc:
                self._index.insert(doc)
                logger.info(f"成功导入文档: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"导入文档失败 [{file_path}]: {e}", exc_info=True)
            return False

    def _load_single_file(self, file_path: str) -> Optional[Document]:
        """加载单个文件为 Document"""
        from llama_index.core import Document

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == ".txt" or ext == ".md":
                with open(file_path, "r", encoding="utf-8") as f:
                    text = f.read()
                return Document(
                    text=text,
                    metadata={
                        "file_name": os.path.basename(file_path),
                        "file_path": file_path,
                    },
                )
            elif ext == ".pdf":
                # 使用 pypdf 解析 PDF
                from pypdf import PdfReader
                reader = PdfReader(file_path)
                text = "\n".join([page.extract_text() for page in reader.pages])
                return Document(
                    text=text,
                    metadata={
                        "file_name": os.path.basename(file_path),
                        "file_path": file_path,
                    },
                )
            elif ext in [".docx", ".doc"]:
                # 使用 python-docx 解析 Word
                from docx import Document as DocxDocument
                doc = DocxDocument(file_path)
                text = "\n".join([p.text for p in doc.paragraphs])
                return Document(
                    text=text,
                    metadata={
                        "file_name": os.path.basename(file_path),
                        "file_path": file_path,
                    },
                )
            elif ext in [".xlsx", ".xls"]:
                # 使用 openpyxl 解析 Excel
                import openpyxl
                wb = openpyxl.load_workbook(file_path, data_only=True)
                text_parts = []
                for sheet in wb.sheetnames:
                    ws = wb[sheet]
                    for row in ws.iter_rows(values_only=True):
                        row_text = " | ".join([str(cell) if cell else "" for cell in row])
                        if row_text.strip():
                            text_parts.append(row_text)
                text = "\n".join(text_parts)
                return Document(
                    text=text,
                    metadata={
                        "file_name": os.path.basename(file_path),
                        "file_path": file_path,
                    },
                )
            else:
                logger.warning(f"不支持的文件类型: {ext}")
                return None
        except Exception as e:
            logger.error(f"解析文件失败 [{file_path}]: {e}")
            return None

    def _get_file_metadata(self, filename: str) -> Dict[str, Any]:
        """获取文件元数据"""
        return {
            "file_name": os.path.basename(filename),
        }

    # ------------------------------------------------------------------
    # 核心搜索接口
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 5, **kwargs) -> SearchResult:
        """
        向量语义搜索

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            SearchResult
        """
        self._ensure_initialized()

        try:
            # 使用 EmbeddingService 对查询进行嵌入（本地离线）
            query_embedding = self._embedding_service.embed_query(query)
            logger.info(f"查询嵌入完成，维度: {len(query_embedding)}")

            # 使用 Chroma 客户端进行向量搜索
            results = self._collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
            )

            logger.info(f"Chroma 搜索返回 {len(results.get('ids', [[]])[0])} 条结果 for query: {query}")

            items: List[KnowledgeItem] = []
            if results.get('ids') and results['ids'][0]:
                for i, doc_id in enumerate(results['ids'][0]):
                    meta = results.get('metadatas', [{}])[0][i] if results.get('metadatas') else {}
                    doc_text = results.get('documents', [[]])[0][i] if results.get('documents') else ""
                    distance = results.get('distances', [[]])[0][i] if results.get('distances') else 0.0
                    # 将距离转换为相似度分数（距离越小，相似度越高）
                    score = 1.0 - distance if distance is not None else 0.0

                    # 处理 tags 可能是字符串（分号分隔）或列表的情况
                    tags_value = meta.get("tags", [])
                    if isinstance(tags_value, str) and tags_value:
                        tags_value = [t.strip() for t in tags_value.split(";") if t.strip()]

                    items.append(
                        KnowledgeItem(
                            id=meta.get("file_path", doc_id),
                            title=meta.get("file_name", meta.get("title", doc_text[:50])),
                            content=doc_text,
                            category=meta.get("category", ""),
                            tags=tags_value,
                            metadata={
                                **meta,
                                "score": score,
                            },
                        )
                    )

            return SearchResult(
                items=items,
                total=len(items),
                query=query,
            )
        except Exception as e:
            logger.error(f"知识库搜索失败: {e}", exc_info=True)
            raise

    def get_by_id(self, knowledge_id: str) -> Optional[KnowledgeItem]:
        """根据 ID 精确查找（通过文件路径）"""
        # Chroma 不直接支持 ID 查询，可以通过元数据过滤
        # 这里简化为返回 None
        return None

    def add(self, item: KnowledgeItem) -> bool:
        """添加单条知识条目"""
        self._ensure_initialized()

        try:
            doc = Document(
                text=item.content,
                metadata={
                    "item_id": item.id,
                    "title": item.title,
                    "category": item.category or "",
                    "tags": ";".join(item.tags) if item.tags else "",
                },
            )
            self._index.insert(doc)
            logger.info(f"成功添加知识条目: {item.id}")
            return True
        except Exception as e:
            logger.error(f"添加知识条目失败 [{item.id}]: {e}", exc_info=True)
            return False

    def add_batch(self, items: List[KnowledgeItem]) -> bool:
        """批量添加知识条目"""
        self._ensure_initialized()

        if not items:
            return True

        try:
            documents = [
                Document(
                    text=item.content,
                    metadata={
                        "item_id": item.id,
                        "title": item.title,
                        "category": item.category or "",
                        "tags": ";".join(item.tags) if item.tags else "",
                    },
                )
                for item in items
            ]
            for doc in documents:
                self._index.insert(doc)
            logger.info(f"成功批量添加 {len(items)} 条知识条目")
            return True
        except Exception as e:
            logger.error(f"批量添加知识条目失败: {e}", exc_info=True)
            return False

    def get_stats(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        self._ensure_initialized()

        try:
            count = self._collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection_name,
                "embedding_model": self.embedding_model,
            }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            return {"error": str(e)}


# ------------------------------------------------------------------
# 单例工厂
# ------------------------------------------------------------------

_default_knowledge_base: Optional[ChromaKnowledgeBase] = None
_init_failed: bool = False


def get_chroma_knowledge_base(
    config: Optional[Dict[str, Any]] = None,
) -> ChromaKnowledgeBase:
    """
    获取 Chroma 知识库单例
    """
    global _default_knowledge_base, _init_failed
    if _init_failed:
        # 如果之前初始化失败，不重试
        raise RuntimeError("Chroma 知识库初始化失败，请检查配置和模型文件")
    if _default_knowledge_base is None:
        try:
            _default_knowledge_base = ChromaKnowledgeBase(config=config)
            # 预热：确保初始化成功
            _default_knowledge_base._ensure_initialized()
        except Exception as e:
            _init_failed = True
            logger.error(f"Chroma 知识库初始化失败: {e}", exc_info=True)
            raise
    return _default_knowledge_base


__all__ = ["ChromaKnowledgeBase", "get_chroma_knowledge_base"]
