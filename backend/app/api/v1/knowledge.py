"""
Knowledge base APIs for search, import, graph, and admin stats.
"""
from __future__ import annotations

import os
import shutil
import time
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field

from app.config import settings
from app.core.permissions import get_current_user
from app.knowledge.chroma_knowledge import get_chroma_knowledge_base
from app.knowledge.neo4j_client import get_neo4j_client
from app.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库查询"])


def _normalize_rel_type(rel_type: str) -> str:
    rel = rel_type or ""
    return rel if rel in _REL_LABEL_MAP else rel.lower()


def _rel_label(rel_type: str) -> str:
    return _REL_LABEL_MAP.get(_normalize_rel_type(rel_type), rel_type)


def _rel_category(rel_type: str) -> str:
    return _REL_CATEGORY_MAP.get(_normalize_rel_type(rel_type), "other")


def _node_category(labels: Optional[List[str]]) -> str:
    label_set = set(labels or [])
    for category in _NODE_LABEL_MAP:
        if category in label_set:
            return category
    return "Other"


def _node_label(category: str) -> str:
    return _NODE_LABEL_MAP.get(category, category)


def _clean_graph_filter(values: Optional[List[str]], allowed_values: set[str]) -> Optional[List[str]]:
    if not values:
        return None
    cleaned = [value for value in values if value in allowed_values]
    return cleaned or None


def _clean_relation_filter(values: Optional[List[str]]) -> Optional[List[str]]:
    if not values:
        return None
    cleaned = [
        _normalize_rel_type(value)
        for value in values
        if _normalize_rel_type(value) in _REL_LABEL_MAP
    ]
    return cleaned or None


def _build_graph_from_neo4j(
    entity: str,
    depth: int = 2,
    limit: int = 60,
    node_labels: Optional[List[str]] = None,
    relation_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    client = get_neo4j_client()

    cypher_hop1 = (
        "MATCH (center {name: $name})-[r1]->(n1) "
        "RETURN center.name AS src, labels(center) AS src_labels, "
        "type(r1) AS rel, n1.name AS tgt, labels(n1) AS tgt_labels "
        f"LIMIT {limit}"
    )
    cypher_hop2 = (
        "MATCH (center {name: $name})-[r1]->(n1)-[r2]->(n2) "
        "WHERE n2.name <> $name "
        "RETURN n1.name AS src, labels(n1) AS src_labels, "
        "type(r2) AS rel, n2.name AS tgt, labels(n2) AS tgt_labels "
        f"LIMIT {limit}"
    )

    allowed_node_labels = set(node_labels or [])
    allowed_relation_types = {
        _normalize_rel_type(rel)
        for rel in relation_types or []
        if _normalize_rel_type(rel) in _REL_LABEL_MAP
    }

    seen_nodes: Dict[str, Dict[str, Any]] = {
        entity: {
            "name": entity,
            "symbolSize": 40,
            "value": entity,
            "category": "Center",
            "labels": ["Center"],
            "hop": 0,
        }
    }
    seen_links: set[tuple[str, str, str]] = set()
    links: list[Dict[str, Any]] = []

    def add_node(name: str, labels: Optional[List[str]], size: int, hop: int) -> None:
        if not name:
            return
        category = _node_category(labels)
        if allowed_node_labels and category not in allowed_node_labels and category != "Center":
            return
        existing = seen_nodes.get(name)
        if existing:
            if hop < existing.get("hop", hop):
                existing["hop"] = hop
            if size > existing.get("symbolSize", size):
                existing["symbolSize"] = size
            if category != "Other" and existing.get("category") in {"Other", "Center"}:
                existing["category"] = category
                existing["labels"] = labels or [category]
            return
        seen_nodes[name] = {
            "name": name,
            "symbolSize": size,
            "value": name,
            "category": category,
            "labels": labels or [category],
            "hop": hop,
        }

    def add_link(src: str, rel: str, tgt: str, tgt_size: int, tgt_labels: Optional[List[str]], hop: int) -> None:
        if not src or not tgt or src not in seen_nodes:
            return
        rel_key = _normalize_rel_type(rel)
        if allowed_relation_types and rel_key not in allowed_relation_types:
            return
        target_category = _node_category(tgt_labels)
        if allowed_node_labels and target_category not in allowed_node_labels:
            return
        if tgt not in seen_nodes:
            add_node(tgt, tgt_labels, tgt_size, hop)
        key = (src, tgt, rel)
        if key in seen_links:
            return
        seen_links.add(key)
        links.append(
            {
                "source": src,
                "target": tgt,
                "relation": rel_key,
                "label": _rel_label(rel),
                "category": _rel_category(rel),
            }
        )

    try:
        for row in client.run(cypher_hop1, {"name": entity}):
            add_node(row["src"], row.get("src_labels"), 40, 0)
            add_link(row["src"], row["rel"], row["tgt"], 28, row.get("tgt_labels"), 1)
        if depth >= 2:
            for row in client.run(cypher_hop2, {"name": entity}):
                add_node(row["src"], row.get("src_labels"), 28, 1)
                add_link(row["src"], row["rel"], row["tgt"], 18, row.get("tgt_labels"), 2)
    except Exception as exc:
        logger.warning(f"Neo4j 图谱查询失败: {exc}")

    nodes = list(seen_nodes.values())
    categories = [
        {"name": category, "label": _node_label(category)}
        for category in sorted({node["category"] for node in nodes})
    ]
    return {"nodes": nodes, "links": links, "categories": categories}


def _get_related_entities_from_graph(entity: str, limit: int = 12) -> List[str]:
    if not entity:
        return []
    try:
        graph = _build_graph_from_neo4j(entity, depth=1, limit=limit)
    except Exception as exc:
        logger.debug(f"获取相关实体失败 [{entity}]: {exc}")
        return []

    related_entities: list[str] = []
    seen = set()
    for link in graph.get("links", []):
        for name in (link.get("source"), link.get("target")):
            if name and name != entity and name not in seen:
                seen.add(name)
                related_entities.append(name)
            if len(related_entities) >= limit:
                return related_entities
    return related_entities


class KnowledgeItemResponse(BaseModel):
    id: str
    title: str
    type: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    content: str
    tags: List[str] = Field(default_factory=list)
    related_entities: List[str] = Field(default_factory=list)
    score: Optional[float] = None


class KnowledgeListResponse(BaseModel):
    items: List[KnowledgeItemResponse]
    total: int
    page: int
    page_size: int


class GraphResponse(BaseModel):
    nodes: List[dict]
    links: List[dict]
    categories: List[dict] = Field(default_factory=list)


_REL_LABEL_MAP = {
    "has_symptom": "症状",
    "acompany_with": "并发症",
    "common_drug": "常用药品",
    "recommand_drug": "推荐药品",
    "need_check": "诊断检查",
    "do_eat": "宜吃",
    "no_eat": "忌吃",
    "recommand_eat": "推荐饮食",
    "belongs_to": "所属科室",
    "drugs_of": "生产药品",
    "治疗": "治疗",
    "相关症状": "相关症状",
    "检查": "检查",
    "临床表现": "临床表现",
    "并发症": "并发症",
}

_NODE_LABEL_MAP = {
    "Center": "中心实体",
    "Disease": "疾病",
    "Symptom": "症状",
    "Drug": "药物",
    "Exam": "检查",
    "BodyPart": "身体部位",
    "Treatment": "治疗",
    "Department": "科室",
    "Food": "饮食",
    "Other": "其他",
}

_REL_CATEGORY_MAP = {
    "has_symptom": "symptom",
    "acompany_with": "complication",
    "common_drug": "drug",
    "recommand_drug": "drug",
    "need_check": "exam",
    "belongs_to": "department",
    "do_eat": "food",
    "no_eat": "food",
    "recommand_eat": "food",
    "drugs_of": "drug",
    "治疗": "treatment",
    "相关症状": "symptom",
    "检查": "exam",
    "临床表现": "symptom",
    "并发症": "complication",
}

_ALLOWED_NODE_LABELS = set(_NODE_LABEL_MAP)
_chroma_kb = None
_chroma_error: Optional[str] = None


def _get_chroma_kb():
    global _chroma_kb, _chroma_error
    if _chroma_kb is None:
        try:
            logger.info("正在初始化 Chroma 知识库")
            _chroma_kb = get_chroma_knowledge_base()
            _chroma_error = None
        except Exception as exc:
            _chroma_error = str(exc)
            logger.error(f"Chroma 知识库初始化失败: {exc}", exc_info=True)
            return None
    return _chroma_kb


@router.get("/search", response_model=KnowledgeListResponse)
async def search_knowledge(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    q: Optional[str] = Query(None, description="兼容参数"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    current_user: dict = Depends(get_current_user),
):
    kw = keyword or q or ""
    if not kw.strip():
        return KnowledgeListResponse(items=[], total=0, page=page, page_size=page_size)

    results: list[Dict[str, Any]] = []
    try:
        chroma_kb = _get_chroma_kb()
        if chroma_kb:
            chroma_result = chroma_kb.search(kw, top_k=page_size * page)
            for item in chroma_result.items:
                results.append(
                    {
                        "id": item.id or f"chroma_{hash(item.title)}",
                        "title": item.title,
                        "type": "document",
                        "category": item.category or "文档",
                        "description": item.content[:100] + "..." if len(item.content) > 100 else item.content,
                        "content": item.content,
                        "tags": item.tags,
                        "related_entities": _get_related_entities_from_graph(item.title),
                        "score": item.metadata.get("score", 0) if item.metadata else 0,
                    }
                )
    except Exception as exc:
        logger.warning(f"Chroma 搜索失败: {exc}", exc_info=True)

    results.sort(key=lambda item: item.get("score", 0), reverse=True)
    total = len(results)
    start = (page - 1) * page_size
    page_results = results[start: start + page_size]

    return KnowledgeListResponse(
        items=[KnowledgeItemResponse(**item) for item in page_results],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/graph", response_model=GraphResponse)
async def get_knowledge_graph(
    entity: str = Query(..., min_length=1, description="实体名称"),
    depth: int = Query(default=2, ge=1, le=3, description="查询深度"),
    limit: int = Query(default=60, ge=10, le=200, description="每跳返回关系数"),
    node_labels: Optional[List[str]] = Query(default=None, description="节点类型过滤"),
    relation_types: Optional[List[str]] = Query(default=None, description="关系类型过滤"),
    current_user: dict = Depends(get_current_user),
):
    client = get_neo4j_client()
    if not client.is_connected:
        raise HTTPException(status_code=503, detail="知识图谱服务暂不可用，请确认 Neo4j 已启动")

    graph = _build_graph_from_neo4j(
        entity,
        depth=depth,
        limit=limit,
        node_labels=_clean_graph_filter(node_labels, _ALLOWED_NODE_LABELS),
        relation_types=_clean_relation_filter(relation_types),
    )
    if len(graph["nodes"]) <= 1:
        raise HTTPException(status_code=404, detail=f"未在知识图谱中找到实体“{entity}”")
    return GraphResponse(**graph)


@router.get("/guidelines", response_model=KnowledgeListResponse)
async def get_clinical_guidelines(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=6, ge=1, le=20, description="每页数量"),
    current_user: dict = Depends(get_current_user),
):
    results: list[KnowledgeItemResponse] = []
    total = 0
    try:
        chroma_kb = _get_chroma_kb()
        if chroma_kb:
            search_queries = ["临床指南", "指南", "诊疗指南", "治疗指南"]
            all_items: list[Dict[str, Any]] = []
            seen_titles = set()
            for query in search_queries:
                try:
                    chroma_result = chroma_kb.search(query, top_k=50)
                    for item in chroma_result.items:
                        if item.title in seen_titles:
                            continue
                        seen_titles.add(item.title)
                        all_items.append(
                            {
                                "id": item.id or f"chroma_{hash(item.title)}",
                                "title": item.title,
                                "type": "guideline",
                                "category": item.category or "临床指南",
                                "description": item.content[:100] + "..." if len(item.content) > 100 else item.content,
                                "content": item.content,
                                "tags": item.tags,
                                "related_entities": [],
                                "score": item.metadata.get("score", 0) if item.metadata else 0,
                            }
                        )
                except Exception as exc:
                    logger.warning(f"搜索 '{query}' 失败: {exc}")

            all_items.sort(key=lambda item: item.get("score", 0), reverse=True)
            total = len(all_items)
            start = (page - 1) * page_size
            page_results = all_items[start: start + page_size]
            results = [KnowledgeItemResponse(**item) for item in page_results]
    except Exception as exc:
        logger.warning(f"获取临床指南失败: {exc}")

    return KnowledgeListResponse(items=results, total=total, page=page, page_size=page_size)


@router.post("/import/file")
async def import_document(
    file: UploadFile = File(..., description="待导入文件"),
    current_user: dict = Depends(get_current_user),
):
    allowed_extensions = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"}
    file_ext = os.path.splitext(file.filename or "")[1].lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型。当前支持: {', '.join(sorted(allowed_extensions))}",
        )

    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"kb_{int(time.time())}_{file.filename}")

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        chroma_kb = _get_chroma_kb()
        if not chroma_kb:
            raise HTTPException(status_code=503, detail="知识库服务暂不可用")

        success = chroma_kb.ingest_file(file_path)
        if not success:
            raise HTTPException(status_code=500, detail="文档导入失败")

        return {
            "status": "success",
            "message": f"文档 '{file.filename}' 导入成功",
            "file_path": file_path,
            "upload_dir": upload_dir,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"导入文档失败: {exc}")
        raise HTTPException(status_code=500, detail=f"导入失败: {exc}") from exc
    finally:
        await file.close()


@router.post("/import/directory")
async def import_directory(
    directory: str = Query(..., description="待导入目录"),
    recursive: bool = Query(default=True, description="是否递归扫描子目录"),
    current_user: dict = Depends(get_current_user),
):
    if not os.path.isdir(directory):
        raise HTTPException(status_code=400, detail=f"目录不存在: {directory}")

    try:
        chroma_kb = _get_chroma_kb()
        if not chroma_kb:
            raise HTTPException(status_code=503, detail="知识库服务暂不可用")
        count = chroma_kb.ingest_directory(directory, recursive=recursive)
        return {
            "status": "success",
            "message": f"成功导入 {count} 个文档",
            "directory": directory,
            "note": "此操作不会复制目录内文件，只会读取并写入向量库。",
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"批量导入失败: {exc}")
        raise HTTPException(status_code=500, detail=f"导入失败: {exc}") from exc


@router.get("/stats")
async def get_knowledge_stats(current_user: dict = Depends(get_current_user)):
    stats: Dict[str, Any] = {
        "upload_dir": settings.UPLOAD_DIR,
        "chroma": {
            "status": "loading",
            "embedding_model": settings.CHROMA_EMBEDDING_MODEL,
            "model_cache_dir": settings.CHROMA_MODEL_CACHE_DIR,
            "persist_dir": settings.CHROMA_PERSIST_DIR,
            "total_documents": 0,
            "error": None,
        },
    }

    try:
        chroma_kb = _get_chroma_kb()
        if chroma_kb:
            chroma_stats = chroma_kb.get_stats()
            stats["chroma"].update(chroma_stats)
            stats["chroma"]["status"] = "ready" if not chroma_stats.get("error") else "failed"
        else:
            stats["chroma"]["status"] = "failed"
            stats["chroma"]["error"] = _chroma_error or "Chroma 未初始化"
    except Exception as exc:
        logger.warning(f"获取 Chroma 统计信息失败: {exc}")
        stats["chroma"]["status"] = "failed"
        stats["chroma"]["error"] = str(exc)

    return stats


@router.get("/{knowledge_id}", response_model=KnowledgeItemResponse)
async def get_knowledge_item(
    knowledge_id: str,
    current_user: dict = Depends(get_current_user),
):
    try:
        chroma_kb = _get_chroma_kb()
        if chroma_kb:
            item = chroma_kb.get_by_id(knowledge_id)
            if item:
                return KnowledgeItemResponse(
                    id=item.id,
                    title=item.title,
                    type="document",
                    category=item.category or "文档",
                    description=item.content[:100] + "..." if len(item.content) > 100 else item.content,
                    content=item.content,
                    tags=item.tags,
                    related_entities=_get_related_entities_from_graph(item.title),
                    score=item.metadata.get("score", 0) if item.metadata else 0,
                )
    except Exception as exc:
        logger.warning(f"获取知识条目失败: {exc}")

    raise HTTPException(status_code=404, detail=f"知识条目 '{knowledge_id}' 不存在")


__all__ = ["router"]
