# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '.')

print("1. 开始导入...")
from app.knowledge.chroma_knowledge import get_chroma_knowledge_base

print("2. 获取知识库...")
kb = get_chroma_knowledge_base()

print("3. 执行搜索...")
result = kb.search('心脏病', top_k=3)

print(f"Search total: {result.total}")
print(f"Items count: {len(result.items)}")
for i, item in enumerate(result.items):
    print(f"Item {i+1}: {item.title[:50]} | score: {item.metadata.get('score')}")

print("完成!")
