import psycopg
from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger
from src.lucidpanda.services.embedding_service import embedding_service
from src.lucidpanda.db.ontology_repo import OntologyRepo

def migrate_entity_registry_vectors():
    """
    为 entity_registry 添加 embedding_vec vector(768) 列并进行数据回填。
    在启动系统向量匹配兜底前，必须执行一次本脚本。
    """
    logger.info("🚀 正在初始化 entity_registry 的向量列和数据回填...")
    
    conn_str = f"host={settings.POSTGRES_HOST} port={settings.POSTGRES_PORT} user={settings.POSTGRES_USER} password={settings.POSTGRES_PASSWORD} dbname={settings.POSTGRES_DB}"
    
    try:
        conn = psycopg.connect(conn_str, row_factory=__import__('psycopg.rows', fromlist=['dict_row']).dict_row)
        cursor = conn.cursor()
        
        # 1. 增加 embedding_vec 列 (如果不存在)
        logger.info("🛠️ 正在修改 entity_registry 增加 embedding_vec 列...")
        cursor.execute("""
            ALTER TABLE entity_registry
            ADD COLUMN IF NOT EXISTS embedding_vec vector(768);
        """)
        
        # 2. 增加 hnsw 索引
        logger.info("🏗️ 正在创建 HNSW 索引 (idx_entity_embedding_hnsw)...")
        cursor.execute("DROP INDEX IF EXISTS idx_entity_embedding_hnsw;")
        cursor.execute("""
            CREATE INDEX idx_entity_embedding_hnsw
            ON entity_registry USING hnsw (embedding_vec vector_cosine_ops)
            WITH (m = 16, ef_construction = 128);
        """)
        conn.commit()

        # 3. 获取所有需要回填的数据
        logger.info("📥 正在读取所有实体现有基础信息...")
        repo = OntologyRepo()
        entities = repo.get_all_entities_with_aliases()
        
        updated = 0
        for ent in entities:
            # 获取显示名称作为基准向量化。可以加上 alias 一起。
            # 这里简化：仅以 display_name 作 vector，因为长尾词直接用 alias string matching，无法 match 上的通常是各种称谓混合，用 name 的核心语义接近也能兜底。
            name = ent.get('display_name')
            if not name:
                continue
                
            try:
                vec = embedding_service.encode(name)
                repo.update_entity_vector(ent['canonical_id'], vec)
                updated += 1
            except Exception as e:
                logger.warning(f"未能将实体 {name} 向量化: {e}")
        
        logger.info(f"🎉 entity_registry 向量化完成！共更新 {updated} 个实体记录。")
        
    except Exception as e:
        logger.error(f"❌ 迁移实体库向量列失败: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_entity_registry_vectors()
