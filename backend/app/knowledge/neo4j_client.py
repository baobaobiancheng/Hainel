"""
Neo4j 客户端
封装 Neo4j 驱动，提供连接管理与基础 Cypher 操作
"""
from typing import List, Dict, Any, Optional
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver
from neo4j.exceptions import ServiceUnavailable

from app.config import settings
from app.utils.logger import get_logger

logger = get_logger(__name__)


class Neo4jClient:
    """Neo4j 连接管理与基础操作"""

    def __init__(self):
        self._driver: Optional[Driver] = None
        self._connect()

    # ── 连接 ──────────────────────────────────────
    def _connect(self):
        try:
            self._driver = GraphDatabase.driver(
                settings.NEO4J_URI,
                auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
                max_connection_pool_size=settings.NEO4J_MAX_CONNECTION_POOL_SIZE,
            )
            self._driver.verify_connectivity()
            logger.info(f"Neo4j 连接成功: {settings.NEO4J_URI}")
        except ServiceUnavailable as e:
            logger.error(f"Neo4j 连接失败: {e}")
            self._driver = None
        except Exception as e:
            logger.error(f"Neo4j 初始化异常: {e}")
            self._driver = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    @contextmanager
    def session(self):
        if not self._driver:
            raise RuntimeError("Neo4j 未连接，请检查服务是否启动")
        with self._driver.session(database=settings.NEO4J_DATABASE) as s:
            yield s

    def close(self):
        if self._driver:
            self._driver.close()
            logger.info("Neo4j 连接已关闭")

    # ── 基础 CRUD ─────────────────────────────────
    def run(self, cypher: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """执行 Cypher 语句并返回记录列表"""
        with self.session() as s:
            result = s.run(cypher, parameters or {})
            return [dict(record) for record in result]

    def run_write(self, cypher: str, parameters: Optional[Dict] = None) -> None:
        """执行写入 Cypher（不关心返回值）"""
        with self.session() as s:
            s.run(cypher, parameters or {})

    # ── 节点操作 ──────────────────────────────────
    def merge_node(self, label: str, props: Dict[str, Any]) -> None:
        """MERGE 节点（按 name 字段去重）"""
        cypher = f"MERGE (n:{label} {{name: $name}}) SET n += $props"
        self.run_write(cypher, {"name": props.get("name", ""), "props": props})

    def merge_nodes_batch(self, label: str, nodes: List[Dict[str, Any]]) -> None:
        """批量 MERGE 节点"""
        cypher = f"UNWIND $nodes AS node MERGE (n:{label} {{name: node.name}}) SET n += node"
        with self.session() as s:
            s.run(cypher, {"nodes": nodes})

    # ── 关系操作 ──────────────────────────────────
    def merge_relation(
        self,
        subj_label: str,
        subj_name:  str,
        relation:   str,
        obj_label:  str,
        obj_name:   str,
        props:      Optional[Dict] = None,
    ) -> None:
        """MERGE 两节点间的有向关系"""
        safe_rel = relation.replace(" ", "_").upper()
        cypher = (
            f"MATCH (a:{subj_label} {{name: $subj}}) "
            f"MATCH (b:{obj_label}  {{name: $obj}}) "
            f"MERGE (a)-[r:{safe_rel}]->(b) "
            f"SET r += $props"
        )
        self.run_write(cypher, {"subj": subj_name, "obj": obj_name, "props": props or {}})

    def merge_relations_batch(self, triples: List[Dict[str, Any]]) -> None:
        """
        批量 MERGE 关系
        triples 格式: [{"subj": str, "subj_label": str, "rel": str, "obj": str, "obj_label": str}]
        """
        for t in triples:
            try:
                self.merge_relation(
                    t["subj_label"], t["subj"],
                    t["rel"],
                    t["obj_label"],  t["obj"],
                )
            except Exception as e:
                logger.warning(f"关系写入失败 {t}: {e}")

    # ── 查询辅助 ──────────────────────────────────
    def get_neighbors(
        self,
        node_name:  str,
        node_label: str = "",
        depth:      int = 1,
        limit:      int = 20,
    ) -> List[Dict[str, Any]]:
        """获取节点的邻居（及关系类型）"""
        label_filter = f":{node_label}" if node_label else ""
        cypher = (
            f"MATCH (n{label_filter} {{name: $name}})-[r*1..{depth}]-(m) "
            f"RETURN n.name AS source, type(r[0]) AS relation, m.name AS target, labels(m) AS target_labels "
            f"LIMIT {limit}"
        )
        return self.run(cypher, {"name": node_name})

    def search_nodes(
        self,
        keyword:    str,
        node_label: str = "",
        limit:      int = 10,
    ) -> List[Dict[str, Any]]:
        """按名称模糊搜索节点"""
        label_filter = f":{node_label}" if node_label else ""
        cypher = (
            f"MATCH (n{label_filter}) WHERE n.name CONTAINS $kw "
            f"RETURN n.name AS name, labels(n) AS labels LIMIT {limit}"
        )
        return self.run(cypher, {"kw": keyword})

    def get_stats(self) -> Dict[str, int]:
        """获取图谱统计信息"""
        node_count = self.run("MATCH (n) RETURN count(n) AS cnt")[0]["cnt"]
        rel_count  = self.run("MATCH ()-[r]->() RETURN count(r) AS cnt")[0]["cnt"]
        return {"nodes": node_count, "relations": rel_count}

    # ── 索引初始化 ────────────────────────────────
    def init_indexes(self) -> None:
        """创建常用节点索引（幂等）"""
        index_ddl = [
            "CREATE INDEX IF NOT EXISTS FOR (n:Disease)   ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Drug)      ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Symptom)   ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:BodyPart)  ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Exam)      ON (n.name)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Treatment) ON (n.name)",
        ]
        for ddl in index_ddl:
            try:
                self.run_write(ddl)
            except Exception as e:
                logger.debug(f"索引创建跳过: {e}")
        logger.info("Neo4j 索引初始化完成")


# ── 单例 ──────────────────────────────────────
_client: Optional[Neo4jClient] = None


def get_neo4j_client() -> Neo4jClient:
    global _client
    if _client is None:
        _client = Neo4jClient()
    return _client
