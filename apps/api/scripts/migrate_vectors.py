import psycopg
from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger

def migrate_vector_dimension():
    """
    将 intelligence 表中的 embedding_vec 维度从 384 迁移到 768。
    """
    logger.info("🚀 正在检查并迁移向量维度 (384 -> 768)...")
    
    conn_str = f"host={settings.POSTGRES_HOST} port={settings.POSTGRES_PORT} user={settings.POSTGRES_USER} password={settings.POSTGRES_PASSWORD} dbname={settings.POSTGRES_DB}"
    
    try:
        conn = psycopg.connect(row_factory=__import__('psycopg.rows', fromlist=['dict_row']).dict_row, conn_str)
        cursor = conn.cursor()
        
        # 1. 检查当前维度
        cursor.execute("""
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'intelligence'::regclass 
              AND attname = 'embedding_vec';
        """)
        row = cursor.fetchone()
        
        if row:
            current_dim = row[0]
            if current_dim == 768:
                logger.info("✅ 维度已经是 768，无需迁移。")
                return
            else:
                logger.info(f"⚠️ 发现旧维度: {current_dim}, 开始执行迁移...")
        else:
            logger.info("ℹ️ 未发现 embedding_vec 列，base.py 的 _init_db 将负责初始化。")
            return

        # 2. 迁移步骤
        # a. 清理重复数据 (生产环境可能存在重复 source_id 导致 Unique 索引冲突)
        logger.info("🧹 发现潜在重复条目，正在清理重复的 source_id...")
        cursor.execute("DELETE FROM intelligence a USING intelligence b WHERE a.id < b.id AND a.source_id = b.source_id;")
        
        # b. 删除索引
        logger.info("🗑️ 正在删除旧索引 idx_intel_embedding_hnsw...")
        cursor.execute("DROP INDEX IF EXISTS idx_intel_embedding_hnsw;")
        
        # b. 修改列类型 (必须先清空数据，因为维度不兼容)
        logger.info("🔄 正在清空旧向量数据并修改列类型为 vector(768)...")
        cursor.execute("UPDATE intelligence SET embedding_vec = NULL;")
        cursor.execute("ALTER TABLE intelligence ALTER COLUMN embedding_vec TYPE vector(768);")
        
        # c. 重建索引
        logger.info("🏗️ 正在重建 HNSW 索引 (ef_construction=128)...")
        cursor.execute("""
            CREATE INDEX idx_intel_embedding_hnsw
            ON intelligence USING hnsw (embedding_vec vector_cosine_ops)
            WITH (m = 16, ef_construction = 128);
        """)
        
        conn.commit()
        logger.info("🎉 向量维度迁移完成 (768)！")
        
    except Exception as e:
        logger.error(f"❌ 迁移失败: {e}")
        if 'conn' in locals():
            conn.rollback()
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    migrate_vector_dimension()
