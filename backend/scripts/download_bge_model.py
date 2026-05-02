#!/usr/bin/env python3
"""
下载 bge-m3 Embedding 模型
在后台运行，不阻塞主进程
"""
import os
import sys

# 设置缓存目录
cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "bge-m3")
os.makedirs(cache_dir, exist_ok=True)

print(f"开始下载 bge-m3 模型到: {cache_dir}")
print("这可能需要几分钟时间，取决于网络速度...")

try:
    from sentence_transformers import SentenceTransformer

    # 下载并缓存模型
    model = SentenceTransformer('BAAI/bge-m3', cache_folder=cache_dir)

    print(f"模型下载完成！缓存路径: {cache_dir}")
    print(f"模型包含的files: {os.listdir(cache_dir) if os.path.exists(cache_dir) else 'N/A'}")

except Exception as e:
    print(f"下载失败: {e}")
    sys.exit(1)
