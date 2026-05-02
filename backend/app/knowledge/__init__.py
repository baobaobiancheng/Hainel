"""
知识库模块（Milvus Lite 向量库 + Neo4j 知识图谱）
"""
from app.knowledge.base import BaseKnowledgeBase, KnowledgeItem, SearchResult
from app.knowledge.search import MilvusLiteKnowledgeBase, get_knowledge_base
from app.knowledge.neo4j_client import Neo4jClient, get_neo4j_client
from app.knowledge.kg_service import (
    KGBuilder,
    KGQueryService,
    get_kg_builder,
    get_kg_query_service,
)

__all__ = [
    # 向量知识库
    "BaseKnowledgeBase",
    "KnowledgeItem",
    "SearchResult",
    "MilvusLiteKnowledgeBase",
    "get_knowledge_base",
    # Neo4j 知识图谱
    "Neo4jClient",
    "get_neo4j_client",
    "KGBuilder",
    "KGQueryService",
    "get_kg_builder",
    "get_kg_query_service",
]
