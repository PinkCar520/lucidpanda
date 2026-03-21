"""
创建信源统计表的迁移脚本
=========================
用于 RSS 信源动态自适应间隔功能
"""
import sys
import os

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.core.logger import logger
from src.lucidpanda.db.base import DBBase


def create_feed_statistics_table():
    """创建 feed_statistics 表"""
    
    db = DBBase()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS feed_statistics (
        feed_name VARCHAR(255) PRIMARY KEY,
        feed_url TEXT,
        category VARCHAR(50),
        
        -- 动态间隔控制
        current_interval INTEGER DEFAULT 120,  -- 当前间隔 (秒)
        min_interval INTEGER DEFAULT 30,       -- 最小间隔
        max_interval INTEGER DEFAULT 1800,     -- 最大间隔
        
        -- 统计指标
        consecutive_empty_count INTEGER DEFAULT 0,
        total_fetches INTEGER DEFAULT 0,
        total_new_items INTEGER DEFAULT 0,
        last_fetch_at TIMESTAMPTZ,
        last_new_item_at TIMESTAMPTZ,
        
        -- 元数据
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        
        CONSTRAINT chk_current_interval CHECK (current_interval > 0),
        CONSTRAINT chk_consecutive_empty CHECK (consecutive_empty_count >= 0),
        CONSTRAINT chk_total_fetches CHECK (total_fetches >= 0),
        CONSTRAINT chk_total_new_items CHECK (total_new_items >= 0)
    );
    
    -- 创建索引
    CREATE INDEX IF NOT EXISTS idx_feed_category ON feed_statistics(category);
    CREATE INDEX IF NOT EXISTS idx_feed_last_fetch ON feed_statistics(last_fetch_at);
    CREATE INDEX IF NOT EXISTS idx_feed_updated_at ON feed_statistics(updated_at);
    
    -- 创建注释
    COMMENT ON TABLE feed_statistics IS 'RSS 信源统计表 - 用于动态自适应间隔';
    COMMENT ON COLUMN feed_statistics.current_interval IS '当前采集间隔 (秒)';
    COMMENT ON COLUMN feed_statistics.consecutive_empty_count IS '连续空返回次数';
    COMMENT ON COLUMN feed_statistics.total_fetches IS '总采集次数';
    COMMENT ON COLUMN feed_statistics.total_new_items IS '总新增情报数';
    """
    
    try:
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_sql)
                conn.commit()
        
        logger.info("✅ feed_statistics 表创建成功")
        
        # 初始化所有信源的统计记录
        from src.lucidpanda.providers.data_sources.rsshub import TIER1_FEEDS_CONFIG
        
        init_data_sql = """
        INSERT INTO feed_statistics (feed_name, feed_url, category, current_interval)
        VALUES %s
        ON CONFLICT (feed_name) DO NOTHING
        """
        
        # 使用 execute_values 批量插入
        from psycopg2.extras import execute_values
        
        values = [
            (feed['name'], feed['url'], feed['category'], 120)
            for feed in TIER1_FEEDS_CONFIG
        ]
        
        with db.get_connection() as conn:
            with conn.cursor() as cursor:
                execute_values(
                    cursor,
                    """
                    INSERT INTO feed_statistics (feed_name, feed_url, category, current_interval)
                    VALUES %s
                    ON CONFLICT (feed_name) DO NOTHING
                    """,
                    values
                )
                conn.commit()
        
        logger.info(f"✅ 已初始化 {len(TIER1_FEEDS_CONFIG)} 个信源的统计记录")
        
    except Exception as e:
        logger.error(f"❌ 创建 feed_statistics 表失败：{e}")
        raise


if __name__ == "__main__":
    create_feed_statistics_table()
