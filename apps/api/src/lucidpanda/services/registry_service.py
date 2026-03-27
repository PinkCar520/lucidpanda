"""
services/registry_service.py — 实体注册与标签动态加载服务
======================================================
管理基于数据库的 Ontology 元数据映射。
"""

import threading

from src.lucidpanda.core.logger import logger
from src.lucidpanda.db.ontology_repo import OntologyRepo


class RegistryService:
    """提供本体元数据的查询与热加载服务"""

    def __init__(self, repo: OntologyRepo):
        self.repo = repo
        self._entity_cache: dict[str, str] = {}  # alias -> canonical_id
        self._taxonomy_cache: list[dict[str, str]] = []
        self._lock = threading.Lock()

        # 初始加载
        self.refresh_cache()

    def refresh_cache(self):
        """从数据库全量同步元数据到内存"""
        logger.info("📡 刷新实体注册表与标签体系缓存...")

        # 加载实体别名映射
        raw_entities = self.repo.get_all_entities_with_aliases()
        new_entity_cache = {}
        for row in raw_entities:
            cid = row["canonical_id"]
            # 将 Canonical_ID 本身作为别名（方便 AI 直接输出 ID 时命中）
            new_entity_cache[cid.lower()] = cid

            # 加载别名并扁平化
            aliases = row.get("aliases") or []
            for alias in aliases:
                new_entity_cache[alias.lower()] = cid

        # 加载分类树
        new_taxonomy = self.repo.get_full_taxonomy()

        with self._lock:
            self._entity_cache = new_entity_cache
            self._taxonomy_cache = new_taxonomy

        logger.info(
            f"✅ 本体缓存已更新: {len(self._entity_cache)} 个别名, {len(self._taxonomy_cache)} 个标签维度。"
        )

    def get_entity_mappings(self) -> dict[str, str]:
        """获取全量别名映射表 (小写映射)"""
        with self._lock:
            return self._entity_cache.copy()

    def get_taxonomy_config(self) -> list[dict[str, str]]:
        """获取打标体系配置"""
        with self._lock:
            return self._taxonomy_cache.copy()

    def find_closest_entity(self, vector, threshold: float = 0.90) -> str | None:
        """代理调用 repo 的向量匹配兜底"""
        return self.repo.find_closest_entity(vector, threshold)

    def register_entity(
        self,
        canonical_id: str,
        display_name: str,
        entity_type: str,
        aliases: list[str] | None = None,
    ):
        """动态增加实体（并异步刷新缓存）"""
        self.repo.upsert_entity(canonical_id, display_name, entity_type)
        if aliases:
            for alias in aliases:
                self.repo.add_alias(canonical_id, alias)
        self.refresh_cache()
