"""
知识图谱构建脚本
从 data/kg_source/ 目录下的文本文件中抽取三元组并写入 Neo4j

用法（在 backend/ 目录下执行）：
    python -m scripts.build_kg
    python -m scripts.build_kg --source data/kg_source --limit 500
"""
import argparse
import sys
import json
from pathlib import Path

# 将 backend 目录加入 sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.neo4j_client import get_neo4j_client
from app.knowledge.kg_service import get_kg_builder
from app.utils.logger import get_logger

logger = get_logger("build_kg")

DEFAULT_SOURCE = Path("data/kg_source")


def build_from_directory(source_dir: Path, limit: int = 0) -> None:
    """遍历目录下所有 .txt / .json 文件，批量构建知识图谱"""
    if not source_dir.exists():
        logger.error(f"数据目录不存在: {source_dir}")
        logger.info("请在 data/kg_source/ 下放置医疗文本文件（.txt 或 .json）")
        return

    client  = get_neo4j_client()
    builder = get_kg_builder()

    # 初始化索引
    client.init_indexes()

    texts: list[str] = []

    for file in sorted(source_dir.rglob("*")):
        if file.suffix == ".txt":
            texts += _read_txt(file)
        elif file.suffix == ".json":
            texts += _read_json(file)

    if not texts:
        logger.warning("未找到任何文本，请检查数据目录内容")
        return

    if limit > 0:
        texts = texts[:limit]

    logger.info(f"共 {len(texts)} 条文本，开始构建知识图谱...")
    result = builder.build_from_texts(texts)

    stats = client.get_stats()
    logger.info(
        f"构建完成 | 本次写入: {result['entities']} 实体 / {result['relations']} 关系 "
        f"| 图谱总计: {stats['nodes']} 节点 / {stats['relations']} 关系"
    )


def _read_txt(path: Path) -> list[str]:
    """每行作为一条文本"""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
        return [ln.strip() for ln in lines if ln.strip()]
    except Exception as e:
        logger.warning(f"读取 {path} 失败: {e}")
        return []


def _read_json(path: Path) -> list[str]:
    """
    支持两种 JSON 格式：
      - 列表：["文本1", "文本2", ...]
      - 对象列表：[{"text": "文本1"}, {"content": "文本2"}, ...]
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            texts = []
            for item in data:
                if isinstance(item, str):
                    texts.append(item)
                elif isinstance(item, dict):
                    texts.append(item.get("text") or item.get("content") or "")
            return [t for t in texts if t.strip()]
    except Exception as e:
        logger.warning(f"读取 {path} 失败: {e}")
    return []


def demo_build() -> None:
    """
    内置演示：写入少量硬编码三元组，用于验证 Neo4j 连通性
    """
    client = get_neo4j_client()
    if not client.is_connected:
        logger.error("Neo4j 未连接，演示终止")
        return

    client.init_indexes()

    demo_nodes = [
        ("Disease",   "高血压"),
        ("Disease",   "冠心病"),
        ("Symptom",   "头痛"),
        ("Symptom",   "胸痛"),
        ("Drug",      "氨氯地平"),
        ("Drug",      "阿司匹林"),
        ("Exam",      "心电图"),
        ("Treatment", "降压治疗"),
    ]
    for label, name in demo_nodes:
        client.merge_node(label, {"name": name})

    demo_relations = [
        ("Disease", "高血压", "相关症状",    "Symptom",   "头痛"),
        ("Disease", "冠心病", "相关症状",    "Symptom",   "胸痛"),
        ("Drug",    "氨氯地平", "治疗",      "Disease",   "高血压"),
        ("Drug",    "阿司匹林", "治疗",      "Disease",   "冠心病"),
        ("Disease", "冠心病", "检查",        "Exam",      "心电图"),
        ("Disease", "高血压", "治疗",        "Treatment", "降压治疗"),
        ("Disease", "高血压", "并发症",      "Disease",   "冠心病"),
    ]
    for sl, sn, rel, ol, on in demo_relations:
        client.merge_relation(sl, sn, rel, ol, on)

    stats = client.get_stats()
    logger.info(f"演示数据写入完成: {stats['nodes']} 节点 / {stats['relations']} 关系")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="医疗知识图谱构建工具")
    parser.add_argument(
        "--source", type=str, default=str(DEFAULT_SOURCE),
        help="医疗文本数据目录（默认 data/kg_source）"
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="处理文本条数上限（0 表示不限）"
    )
    parser.add_argument(
        "--demo", action="store_true",
        help="仅写入演示数据，验证 Neo4j 连接"
    )
    args = parser.parse_args()

    if args.demo:
        demo_build()
    else:
        build_from_directory(Path(args.source), limit=args.limit)
