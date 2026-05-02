"""
将 medical.json 数据导入 Chroma 向量知识库

用法（在 backend/ 目录下）：
    .venv/Scripts/python.exe -m scripts.import_medical_to_chroma
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.knowledge.chroma_knowledge import get_chroma_knowledge_base
from app.knowledge.base import KnowledgeItem
from app.utils.logger import get_logger

logger = get_logger("import_medical_to_chroma")

DEFAULT_FILE = Path("data/medical.json")


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


def convert_to_knowledge_items(records: List[Dict[str, Any]]) -> List[KnowledgeItem]:
    """将 medical.json 记录转换为 KnowledgeItem 列表"""
    items = []

    for i, record in enumerate(records):
        name = record.get("name", "").strip()
        if not name:
            continue

        # 构建内容
        desc = record.get("desc", "")
        cause = record.get("cause", "")
        prevent = record.get("prevent", "")
        symptom = "；".join(record.get("symptom", []))
        cure_way = "；".join(record.get("cure_way", []))
        check = "；".join(record.get("check", []))
        recommand_drug = "；".join(record.get("recommand_drug", []))

        # 组合 content
        content_parts = []
        if desc:
            content_parts.append(f"【描述】{desc}")
        if cause:
            content_parts.append(f"【病因】{cause}")
        if symptom:
            content_parts.append(f"【症状】{symptom}")
        if cure_way:
            content_parts.append(f"【治疗方法】{cure_way}")
        if check:
            content_parts.append(f"【检查项目】{check}")
        if recommand_drug:
            content_parts.append(f"【推荐用药】{recommand_drug}")
        if prevent:
            content_parts.append(f"【预防】{prevent}")

        content = "\n".join(content_parts)

        # 获取分类
        category = record.get("category", [])
        category_str = category[0] if category else "疾病"

        # 构建 tags
        tags = []
        if symptom:
            tags.extend(record.get("symptom", [])[:5])  # 最多5个症状作为标签
        tags.extend(record.get("cure_department", []))

        item = KnowledgeItem(
            id=f"disease_{i}",
            title=name,
            content=content,
            category=category_str,
            tags=tags,
            metadata={},
        )
        items.append(item)

    return items


def main(file_path: Path):
    if not file_path.exists():
        logger.error(f"文件不存在: {file_path}")
        logger.info("请将 medical.json 放到 data/ 目录下，然后重新运行")
        sys.exit(1)

    logger.info(f"开始导入: {file_path}")

    # 读取数据
    records = load_medical_json(file_path)
    if not records:
        logger.error("未读取到任何记录")
        sys.exit(1)

    # 转换为 KnowledgeItem
    items = convert_to_knowledge_items(records)
    logger.info(f"转换得到 {len(items)} 条知识条目")

    # 获取 Chroma 知识库
    logger.info("初始化 Chroma 知识库...")
    kb = get_chroma_knowledge_base()

    # 批量导入
    print("=" * 50)
    print("开始导入到 Chroma 向量库...")
    print("=" * 50)
    batch_size = 100
    total = len(items)
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        kb.add_batch(batch)
        progress = min(i + batch_size, len(items))
        percent = progress * 100 // total
        bar_len = 30
        filled = bar_len * progress // total
        bar = "█" * filled + "░" * (bar_len - filled)
        print(f"[{bar}] {progress}/{total} ({percent}%)")
        sys.stdout.flush()

    # 统计
    stats = kb.get_stats()
    print("=" * 50)
    print(f"导入完成！共 {stats.get('total_documents', 0)} 条文档")
    print("=" * 50)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="medical.json → Chroma 向量库导入工具")
    parser.add_argument(
        "--file", type=str, default=str(DEFAULT_FILE),
        help=f"medical.json 路径（默认: {DEFAULT_FILE}）"
    )
    args = parser.parse_args()
    main(Path(args.file))
