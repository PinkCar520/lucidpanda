"""
scripts/migrate_hnsw.py — HNSW 索引迁移脚本
========================================
确保 intelligence 表的 embedding_vec 字段拥有高性能 HNSW 索引。
"""
import asyncio
import os
import sys

# 确保能导入 src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lucidpanda.core.logger import logger
from src.lucidpanda.db.base import DBBase

# 使用默认配置 (由环境变量覆盖)
pass

async def migrate():
    db = DBBase()
    try:
        with db._get_conn() as conn:
            with conn.cursor() as cursor:
                print("🚀 正在检查并部署 HNSW 索引...")

                # 1. 确保 vector 扩展已安装
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")

                # 2. 确保 embedding_vec 字段存在
                cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS embedding_vec vector(768);")

                # 3. 创建 HNSW 索引
                print("⏳ 正在创建 idx_intel_embedding_hnsw (这可能需要一些时间，取决于数据量)...")
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_intel_embedding_hnsw
                    ON intelligence USING hnsw (embedding_vec vector_cosine_ops)
                    WITH (m = 16, ef_construction = 128);
                """)

                conn.commit()
                print("✅ HNSW 索引部署成功！")

    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        logger.error(f"HNSW Migration Failed: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
