"""
知识图谱服务
提供两类功能：
  1. 图谱构建（KG Builder）：文本 → CWS + NER + RE → Neo4j
  2. 图谱查询（KG Query）：为 LLM 智能体提供结构化知识上下文
"""
from typing import List, Dict, Any, Optional

from app.knowledge.neo4j_client import Neo4jClient, get_neo4j_client
from app.nlp.ner import get_ner, Entity
from app.nlp.relation_extraction import get_relation_extractor
from app.nlp.cws import get_cws
from app.utils.logger import get_logger

logger = get_logger(__name__)

# NER 标签 → Neo4j 节点标签的映射
_ENTITY_LABEL_MAP: Dict[str, str] = {
    "DISEASE":   "Disease",
    "SYMPTOM":   "Symptom",
    "DRUG":      "Drug",
    "EXAM":      "Exam",
    "BODY_PART": "BodyPart",
    "TREATMENT": "Treatment",
}


# ─────────────────────────────────────────────────
# KG 构建器
# ─────────────────────────────────────────────────
class KGBuilder:
    """
    从非结构化医疗文本中抽取三元组并写入 Neo4j

    典型使用场景：
        builder = KGBuilder()
        builder.build_from_text("患者因高血压服用氨氯地平...")
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        self._client = client or get_neo4j_client()
        self._ner    = get_ner()
        self._re     = get_relation_extractor()
        self._cws    = get_cws()

    def build_from_text(self, text: str) -> Dict[str, int]:
        """
        处理单条文本，将实体和关系写入 Neo4j

        Returns:
            {"entities": int, "relations": int}
        """
        # ① 分词（可选，目前用于预处理）
        _ = self._cws.segment(text)

        # ② NER
        ner_result = self._ner.recognize(text)
        entities   = ner_result.entities

        # ③ 关系抽取
        re_result  = self._re.extract(text, entities)
        relations  = re_result.relations

        # ④ 写节点
        entity_count = 0
        for entity in entities:
            node_label = _ENTITY_LABEL_MAP.get(entity.label)
            if node_label:
                try:
                    self._client.merge_node(node_label, {"name": entity.text})
                    entity_count += 1
                except Exception as e:
                    logger.warning(f"节点写入失败 [{entity.text}]: {e}")

        # ⑤ 写关系
        relation_count = 0
        for rel in relations:
            head_label = self._get_entity_label(rel.head, entities)
            tail_label = self._get_entity_label(rel.tail, entities)
            if head_label and tail_label:
                try:
                    self._client.merge_relation(
                        head_label, rel.head,
                        rel.relation,
                        tail_label, rel.tail,
                        {"confidence": rel.confidence},
                    )
                    relation_count += 1
                except Exception as e:
                    logger.warning(f"关系写入失败 [{rel.head}]-[{rel.relation}]->[{rel.tail}]: {e}")

        logger.info(f"文本处理完成: {entity_count} 个实体, {relation_count} 条关系")
        return {"entities": entity_count, "relations": relation_count}

    def build_from_texts(self, texts: List[str]) -> Dict[str, int]:
        """批量处理文本"""
        total_entities   = 0
        total_relations  = 0
        for i, text in enumerate(texts, 1):
            try:
                result = self.build_from_text(text)
                total_entities  += result["entities"]
                total_relations += result["relations"]
            except Exception as e:
                logger.error(f"第 {i} 条文本处理失败: {e}")
            if i % 100 == 0:
                logger.info(f"已处理 {i}/{len(texts)} 条文本")
        return {"entities": total_entities, "relations": total_relations}

    def _get_entity_label(self, text: str, entities: List[Entity]) -> Optional[str]:
        for e in entities:
            if e.text == text:
                return _ENTITY_LABEL_MAP.get(e.label)
        return None


# ─────────────────────────────────────────────────
# KG 查询器
# ─────────────────────────────────────────────────
class KGQueryService:
    """
    面向 LLM 智能体的知识图谱查询服务

    提供结构化知识检索，用于增强 LLM 上下文（RAG + KG 混合）
    """

    def __init__(self, client: Optional[Neo4jClient] = None):
        self._client = client or get_neo4j_client()
        self._ner    = get_ner()

    def query_by_text(self, text: str, depth: int = 2, limit: int = 30) -> Dict[str, Any]:
        """
        从问诊文本中自动抽取实体，并查询相关知识图谱子图

        Returns:
            {
                "entities": [...],      # 识别到的实体
                "knowledge": [...],     # 图谱三元组
                "summary": str,         # 供 LLM 使用的文字摘要
            }
        """
        ner_result = self._ner.recognize(text)
        entities   = ner_result.entities

        triples: List[Dict] = []
        for entity in entities:
            node_label = _ENTITY_LABEL_MAP.get(entity.label, "")
            neighbors  = self._client.get_neighbors(
                entity.text, node_label, depth=depth, limit=limit
            )
            triples.extend(neighbors)

        # 去重
        seen = set()
        unique_triples = []
        for t in triples:
            key = (t.get("source"), t.get("relation"), t.get("target"))
            if key not in seen:
                seen.add(key)
                unique_triples.append(t)

        summary = self._build_summary(entities, unique_triples)

        return {
            "entities": [{"text": e.text, "label": e.label} for e in entities],
            "knowledge": unique_triples,
            "summary": summary,
        }

    def query_disease_info(self, disease_name: str) -> Dict[str, Any]:
        """查询某疾病的全面知识（症状、药物、检查、并发症等）"""
        cypher = """
        MATCH (d:Disease {name: $name})-[r]->(m)
        RETURN type(r) AS relation, m.name AS target, labels(m) AS target_labels
        UNION
        MATCH (m)-[r]->(d:Disease {name: $name})
        RETURN type(r) AS relation, m.name AS target, labels(m) AS source_labels
        LIMIT 50
        """
        rows = self._client.run(cypher, {"name": disease_name})
        return {"disease": disease_name, "relations": rows}

    def query_drug_info(self, drug_name: str) -> Dict[str, Any]:
        """查询某药物的适应症、禁忌、不良反应等信息"""
        cypher = """
        MATCH (d:Drug {name: $name})-[r]->(m)
        RETURN type(r) AS relation, m.name AS target, labels(m) AS target_labels
        LIMIT 30
        """
        rows = self._client.run(cypher, {"name": drug_name})
        return {"drug": drug_name, "relations": rows}

    def search_entities(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """模糊搜索实体节点"""
        return self._client.search_nodes(keyword, limit=limit)

    def get_graph_stats(self) -> Dict[str, int]:
        """获取图谱统计"""
        return self._client.get_stats()

    # ── 内部工具 ──────────────────────────────────
    def _build_summary(
        self, entities: List[Entity], triples: List[Dict]
    ) -> str:
        """将知识三元组整理为供 LLM 使用的文字摘要"""
        if not triples:
            return "暂未在知识图谱中找到相关信息。"

        lines = ["以下是从医疗知识图谱中检索到的相关知识："]
        for t in triples[:20]:          # 避免超出 LLM context 窗口
            src  = t.get("source", "")
            rel  = t.get("relation", "")
            tgt  = t.get("target", "")
            if src and rel and tgt:
                lines.append(f"  · {src} —[{rel}]→ {tgt}")

        if len(triples) > 20:
            lines.append(f"  （另有 {len(triples) - 20} 条关系未展示）")

        return "\n".join(lines)


# ── 单例工厂 ──────────────────────────────────
_builder:      Optional[KGBuilder]      = None
_query_service: Optional[KGQueryService] = None


def get_kg_builder() -> KGBuilder:
    global _builder
    if _builder is None:
        _builder = KGBuilder()
    return _builder


def get_kg_query_service() -> KGQueryService:
    global _query_service
    if _query_service is None:
        _query_service = KGQueryService()
    return _query_service
