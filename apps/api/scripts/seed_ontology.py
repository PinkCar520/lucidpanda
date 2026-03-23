"""
scripts/seed_ontology.py — 本体元数据初始化交互脚本
================================================
将 ontology.py 中的硬编码配置导入 PostgreSQL 数据库。
"""
import asyncio
import os
import sys

# 确保能导入 src
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.lucidpanda.core.ontology import CORE_ENTITIES, TAXONOMY
from src.lucidpanda.db.ontology_repo import OntologyRepo
from src.lucidpanda.config import settings

# 默认使用 settings 中的配置，支持环境覆盖
# settings.POSTGRES_HOST = "127.0.0.1"

async def seed_data():
    print("🌱 正在初始化系统本体数据 (Ontology Seeding)...")
    repo = OntologyRepo()
    
    # 1. 迁移分类体系 (Taxonomy)
    print("\n[1/2] 迁移分类体系...")
    for dimension, values in TAXONOMY.items():
        for val in values:
            repo.upsert_taxonomy(dimension, val)
            print(f"  - 🏷️  Taxonomy: {dimension} -> {val}")

    # 2. 迁移核心实体 (Core Entities)
    print("\n[2/2] 迁移核心实体与别名...")
    for cid, data in CORE_ENTITIES.items():
        repo.upsert_entity(
            canonical_id=cid,
            display_name=data["name"],
            entity_type=data["type"]
        )
        print(f"  - 🏢 Entity: {cid} ({data['name']})")
        
        for alias in data.get("aliases", []):
            repo.add_alias(cid, alias)
            print(f"    - 🔗 Alias: {alias}")

    print("\n✨ 初始化完成！所有元数据已持久化至数据库。")

if __name__ == "__main__":
    asyncio.run(seed_data())
