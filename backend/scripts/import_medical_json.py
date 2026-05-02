"""
medical.json 导入脚本
将刘焕勇医疗知识图谱项目的 medical.json 数据一键导入 Neo4j

用法（在 backend/ 目录下）：
    python -m scripts.import_medical_json
    python -m scripts.import_medical_json --file data/medical.json
    python -m scripts.import_medical_json --file data/medical.json --batch 200

数据来源：https://github.com/liuhuanyong/QASystemOnMedicalKG
数据格式：JSONL（每行一个疾病 JSON 对象）
"""
import sys
import json
import argparse
from pathlib import Path
from typing import List, Set, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.neo4j_client import get_neo4j_client
from app.utils.logger import get_logger

logger = get_logger("import_medical_json")

DEFAULT_FILE = Path("data/medical.json")


# ─────────────────────────────────────────────────
# 数据读取
# ─────────────────────────────────────────────────
def load_medical_json(path: Path) -> List[Dict[str, Any]]:
    """读取 JSONL 格式的 medical.json，每行一个疾病对象"""
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as e:
                logger.warning(f"第 {i} 行解析失败，跳过: {e}")
    logger.info(f"成功读取 {len(records)} 条疾病记录")
    return records


# ─────────────────────────────────────────────────
# 节点收集
# ─────────────────────────────────────────────────
def collect_all_nodes(records: List[Dict]) -> Dict[str, Set[str]]:
    nodes: Dict[str, Set[str]] = {
        "Disease":    set(),
        "Symptom":    set(),
        "Drug":       set(),
        "Food":       set(),
        "Check":      set(),
        "Department": set(),
        "Producer":   set(),
    }

    for d in records:
        name = d.get("name", "").strip()
        if not name:
            continue
        nodes["Disease"].add(name)

        for sym in d.get("symptom", []):
            if sym: nodes["Symptom"].add(sym.strip())

        for drug in d.get("common_drug", []) + d.get("recommand_drug", []):
            if drug: nodes["Drug"].add(drug.strip())

        for food in d.get("do_eat", []) + d.get("not_eat", []) + d.get("recommand_eat", []):
            if food: nodes["Food"].add(food.strip())

        for chk in d.get("check", []):
            if chk: nodes["Check"].add(chk.strip())

        for dep in d.get("cure_department", []):
            if dep: nodes["Department"].add(dep.strip())

        for detail in d.get("drug_detail", []):
            if "(" in detail:
                producer = detail.split("(")[0].strip()
                if producer: nodes["Producer"].add(producer)

    return nodes


# ─────────────────────────────────────────────────
# 批量写节点（使用 UNWIND 高效批量写入）
# ─────────────────────────────────────────────────
def import_nodes(client, nodes: Dict[str, Set[str]], batch_size: int):
    for label, name_set in nodes.items():
        if not name_set:
            continue
        name_list = list(name_set)
        total = len(name_list)

        if label == "Disease":
            continue   # Disease 节点含属性，单独处理

        for i in range(0, total, batch_size):
            chunk = name_list[i:i + batch_size]
            cypher = (
                f"UNWIND $names AS n "
                f"MERGE (:{label} {{name: n}})"
            )
            client.run_write(cypher, {"names": chunk})

        logger.info(f"  {label}: {total} 个节点写入完成")


def import_disease_nodes(client, records: List[Dict], batch_size: int):
    """Disease 节点包含完整属性，单独批量写入"""
    disease_list = []
    for d in records:
        name = d.get("name", "").strip()
        if not name:
            continue
        disease_list.append({
            "name":           name,
            "desc":           d.get("desc",           ""),
            "cause":          d.get("cause",          ""),
            "prevent":        d.get("prevent",        ""),
            "easy_get":       d.get("easy_get",       ""),
            "cure_lasttime":  d.get("cure_lasttime",  ""),
            "cure_way":       "；".join(d.get("cure_way", [])),
            "cured_prob":     d.get("cured_prob",     ""),
        })

    total = len(disease_list)
    for i in range(0, total, batch_size):
        chunk = disease_list[i:i + batch_size]
        cypher = (
            "UNWIND $nodes AS node "
            "MERGE (d:Disease {name: node.name}) "
            "SET d += node"
        )
        client.run_write(cypher, {"nodes": chunk})

    logger.info(f"  Disease: {total} 个节点写入完成")


# ─────────────────────────────────────────────────
# 批量写关系
# ─────────────────────────────────────────────────
def import_relationships(client, records: List[Dict], batch_size: int):
    """
    11 类关系定义（与原项目一致）：
      has_symptom       疾病 → 症状
      acompany_with     疾病 → 并发疾病
      common_drug       疾病 → 常用药品
      recommand_drug    疾病 → 推荐药品
      need_check        疾病 → 检查项目
      do_eat            疾病 → 宜吃食物
      no_eat            疾病 → 忌吃食物
      recommand_eat     疾病 → 推荐食谱
      belongs_to        疾病 → 所属科室
      dept_belongs_to   科室 → 父科室
      drugs_of          厂商 → 药品
    """

    # 收集各类关系对
    rels: Dict[str, List[List[str]]] = {
        "has_symptom":    [],
        "acompany_with":  [],
        "common_drug":    [],
        "recommand_drug": [],
        "need_check":     [],
        "do_eat":         [],
        "no_eat":         [],
        "recommand_eat":  [],
        "belongs_to":     [],   # 疾病 → 科室
        "dept_belongs_to":[],   # 子科室 → 父科室
        "drugs_of":       [],   # Producer → Drug
    }

    for d in records:
        name = d.get("name", "").strip()
        if not name:
            continue

        for sym in d.get("symptom", []):
            if sym: rels["has_symptom"].append([name, sym.strip()])

        for acp in d.get("acompany", []):
            if acp: rels["acompany_with"].append([name, acp.strip()])

        for drug in d.get("common_drug", []):
            if drug: rels["common_drug"].append([name, drug.strip()])

        for drug in d.get("recommand_drug", []):
            if drug: rels["recommand_drug"].append([name, drug.strip()])

        for chk in d.get("check", []):
            if chk: rels["need_check"].append([name, chk.strip()])

        for food in d.get("do_eat", []):
            if food: rels["do_eat"].append([name, food.strip()])

        for food in d.get("not_eat", []):
            if food: rels["no_eat"].append([name, food.strip()])

        for food in d.get("recommand_eat", []):
            if food: rels["recommand_eat"].append([name, food.strip()])

        dept_list = d.get("cure_department", [])
        if len(dept_list) >= 1:
            rels["belongs_to"].append([name, dept_list[-1].strip()])
        if len(dept_list) == 2:
            rels["dept_belongs_to"].append([dept_list[1].strip(), dept_list[0].strip()])

        for detail in d.get("drug_detail", []):
            if "(" in detail:
                producer = detail.split("(")[0].strip()
                drug_name = detail.split("(")[-1].replace(")", "").strip()
                if producer and drug_name:
                    rels["drugs_of"].append([producer, drug_name])

    # Cypher 模板：(start_label)-[rel_type]->(end_label)
    rel_specs = {
        "has_symptom":     ("Disease",    "Symptom",    "has_symptom",    "症状"),
        "acompany_with":   ("Disease",    "Disease",    "acompany_with",  "并发症"),
        "common_drug":     ("Disease",    "Drug",       "common_drug",    "常用药品"),
        "recommand_drug":  ("Disease",    "Drug",       "recommand_drug", "推荐药品"),
        "need_check":      ("Disease",    "Check",      "need_check",     "诊断检查"),
        "do_eat":          ("Disease",    "Food",       "do_eat",         "宜吃"),
        "no_eat":          ("Disease",    "Food",       "no_eat",         "忌吃"),
        "recommand_eat":   ("Disease",    "Food",       "recommand_eat",  "推荐食谱"),
        "belongs_to":      ("Disease",    "Department", "belongs_to",     "所属科室"),
        "dept_belongs_to": ("Department", "Department", "belongs_to",     "属于"),
        "drugs_of":        ("Producer",   "Drug",       "drugs_of",       "生产药品"),
    }

    for rel_key, pairs in rels.items():
        if not pairs:
            continue
        sl, el, rel_type, _ = rel_specs[rel_key]

        # 去重
        unique = list({(p[0], p[1]) for p in pairs})
        total = len(unique)

        cypher = (
            f"UNWIND $pairs AS pair "
            f"MATCH (a:{sl} {{name: pair[0]}}) "
            f"MATCH (b:{el} {{name: pair[1]}}) "
            f"MERGE (a)-[:{rel_type}]->(b)"
        )
        for i in range(0, total, batch_size):
            chunk = [[p[0], p[1]] for p in unique[i:i + batch_size]]
            client.run_write(cypher, {"pairs": chunk})

        logger.info(f"  {rel_type}: {total} 条关系写入完成")


# ─────────────────────────────────────────────────
# 主流程
# ─────────────────────────────────────────────────
def main(file_path: Path, batch_size: int):
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        logger.info("请将 medical.json 放到 data/ 目录下，然后重新运行")
        sys.exit(1)

    client = get_neo4j_client()
    if not client.is_connected:
        logger.error("Neo4j 连接失败，请确认 Neo4j 服务已启动，并检查 .env 中的连接配置")
        sys.exit(1)

    logger.info(f"开始导入: {file_path}")

    # ① 读取数据
    records = load_medical_json(file_path)
    if not records:
        logger.error("未读取到任何记录")
        sys.exit(1)

    # ② 初始化索引
    logger.info("step 1/4  初始化 Neo4j 索引...")
    _init_indexes(client)

    # ③ 导入节点
    logger.info("step 2/4  导入节点...")
    nodes = collect_all_nodes(records)
    for label, s in nodes.items():
        logger.info(f"  {label}: 共 {len(s)} 个")

    import_disease_nodes(client, records, batch_size)
    import_nodes(client, nodes, batch_size)

    # ④ 导入关系
    logger.info("step 3/4  导入关系...")
    import_relationships(client, records, batch_size)

    # ⑤ 统计
    logger.info("step 4/4  统计图谱规模...")
    stats = client.get_stats()
    logger.info(
        f"导入完成！图谱共 {stats['nodes']:,} 个节点 / {stats['relations']:,} 条关系"
    )
    logger.info("打开 http://localhost:7474 可在 Neo4j Browser 中查看图谱")


def _init_indexes(client):
    ddls = [
        "CREATE INDEX IF NOT EXISTS FOR (n:Disease)    ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Drug)       ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Symptom)    ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Food)       ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Check)      ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Department) ON (n.name)",
        "CREATE INDEX IF NOT EXISTS FOR (n:Producer)   ON (n.name)",
    ]
    for ddl in ddls:
        try:
            client.run_write(ddl)
        except Exception:
            pass
    logger.info("  索引创建完成")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="medical.json → Neo4j 导入工具")
    parser.add_argument(
        "--file",  type=str, default=str(DEFAULT_FILE),
        help=f"medical.json 路径（默认: {DEFAULT_FILE}）"
    )
    parser.add_argument(
        "--batch", type=int, default=100,
        help="每批写入条数（默认: 100，内存不足可调小）"
    )
    args = parser.parse_args()
    main(Path(args.file), args.batch)
