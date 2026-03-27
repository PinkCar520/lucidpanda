"""
db/ontology_repo.py — 实体与标签元数据仓库
========================================
负责 entity_registry, entity_aliases 和 taxonomy_registry 的底层 CRUD。
"""

from typing import Any

from src.lucidpanda.core.logger import logger
from src.lucidpanda.db.base import DBBase


class OntologyRepo(DBBase):
    """底层存储适配器，用于加载本体元数据"""

    def get_all_entities_with_aliases(self) -> list[dict[str, Any]]:
        """
        获取所有活跃实体及其对应的别名列表。
        返回格式: [{"canonical_id": "...", "display_name": "...", "aliases": ["...", "..."]}, ...]
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    # 使用聚合查询减少循环
                    cursor.execute("""
                        SELECT 
                            r.canonical_id, 
                            r.display_name, 
                            r.entity_type, 
                            r.importance_weight,
                            array_agg(a.alias) filter (where a.alias is not null) as aliases
                        FROM entity_registry r
                        LEFT JOIN entity_aliases a ON r.canonical_id = a.canonical_id
                        WHERE r.is_active = TRUE
                        GROUP BY r.canonical_id;
                    """)
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Failed to fetch entities from DB: {e}")
            return []

    def get_full_taxonomy(self) -> list[dict[str, Any]]:
        """加载全量分类树配置"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT dimension, value FROM taxonomy_registry;")
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"❌ Failed to fetch taxonomy from DB: {e}")
            return []

    def upsert_entity(
        self,
        canonical_id: str,
        display_name: str,
        entity_type: str,
        weight: float = 1.0,
    ):
        """新增或更新核心实体"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO entity_registry (canonical_id, display_name, entity_type, importance_weight)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (canonical_id) DO UPDATE SET
                            display_name = EXCLUDED.display_name,
                            entity_type = EXCLUDED.entity_type,
                            importance_weight = EXCLUDED.importance_weight,
                            updated_at = CURRENT_TIMESTAMP;
                    """,
                        (canonical_id, display_name, entity_type, weight),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"❌ Upsert Entity Failed: {e}")

    def add_alias(self, canonical_id: str, alias: str):
        """为实体绑定别名"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO entity_aliases (canonical_id, alias)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                    """,
                        (canonical_id, alias),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"❌ Add Alias Failed: {e}")

    def upsert_taxonomy(self, dimension: str, value: str):
        """维护分类维度"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO taxonomy_registry (dimension, value)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING;
                    """,
                        (dimension, value),
                    )
                    conn.commit()
        except Exception as e:
            logger.error(f"❌ Upsert Taxonomy Failed: {e}")

    def find_closest_entity(self, vector, threshold: float = 0.90) -> str | None:
        """通过 embedding_vec 进行向量兜底查询"""
        try:
            vec_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT canonical_id, 1 - (embedding_vec <=> %s::vector) AS sim
                        FROM entity_registry
                        WHERE embedding_vec IS NOT NULL
                        ORDER BY embedding_vec <=> %s::vector
                        LIMIT 1;
                    """,
                        (vec_list, vec_list),
                    )
                    row = cursor.fetchone()
                    if row and row["sim"] >= threshold:
                        return row["canonical_id"]
                    return None
        except Exception as e:
            logger.warning(f"⚠️ 向量匹配实体兜底失败: {e}")
            return None

    def update_entity_vector(self, canonical_id: str, vector) -> None:
        """更新实体的向量"""
        try:
            vec_list = vector.tolist() if hasattr(vector, "tolist") else list(vector)
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE entity_registry
                        SET embedding_vec = %s::vector
                        WHERE canonical_id = %s;
                    """,
                        (vec_list, canonical_id),
                    )
                    conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ 更新实体向量失败 [{canonical_id}]: {e}")
