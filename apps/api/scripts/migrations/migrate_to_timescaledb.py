import os
import sys

import psycopg

# 确保能导入项目中原有的 settings
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, root_dir)

from src.lucidpanda.config import settings  # noqa: E402
from src.lucidpanda.core.logger import logger  # noqa: E402


def migrate_to_timescaledb():
    """
    将旧的历史行情表（快照集市和财务估值）强行融入时序时空的“超表”
    """
    db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

    from src.lucidpanda.db.base import DBBase

    # 1. 确保旧表和基础数据结构已经由 ORM 预热建立
    try:
        DBBase()._init_db()
        logger.info("✅ 确保数据库基础表结构已存在")
    except Exception as e:
        logger.warning(f"⚠️ 预热表结构时发生非致命错误: {e}")

    # 注入的建表魔咒
    sql_commands = [
        # 强制挂载时序插件
        "CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;",

        # 消除普通表带有非时间字段 (id) 的主键排斥约束，否则 TimescaleDB 拒绝时序化
        "ALTER TABLE market_indicators DROP CONSTRAINT IF EXISTS market_indicators_pkey CASCADE;",
        "ALTER TABLE fund_valuation_archive DROP CONSTRAINT IF EXISTS fund_valuation_archive_pkey CASCADE;",

        # 将 market_indicators 转为时序表
        """
        SELECT create_hypertable('market_indicators', 'timestamp',
                                 chunk_time_interval => INTERVAL '1 day',
                                 migrate_data => TRUE,
                                 if_not_exists => TRUE);
        """,

        # 3. 如果存在 fund_valuation_archive（长线资金估值快照），将其归档为超表
        """
        SELECT create_hypertable('fund_valuation_archive', 'trade_date',
                                 chunk_time_interval => INTERVAL '1 day',
                                 migrate_data => TRUE,
                                 if_not_exists => TRUE);
        """,

        # 4. 开启时序空间压缩秘术（极大地省空间）
        """
        ALTER TABLE market_indicators SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'indicator_name'
        );
        """,
        "SELECT add_compression_policy('market_indicators', INTERVAL '30 days', if_not_exists => TRUE);",

        """
        ALTER TABLE fund_valuation_archive SET (
            timescaledb.compress,
            timescaledb.compress_segmentby = 'fund_code'
        );
        """,
        "SELECT add_compression_policy('fund_valuation_archive', INTERVAL '100 days', if_not_exists => TRUE);"
    ]

    try:
        with psycopg.connect(db_url) as conn:
            # 开启自动提交或者保证不在事务黑洞中卡死（有些 extension 需要 non-transactional）
            conn.autocommit = True
            with conn.cursor() as cur:
                for sql in sql_commands:
                    try:
                        cur.execute(sql)
                        logger.info(f"✅ 执行成功: {sql.strip()[:60]}...")
                    except psycopg.errors.DuplicateObject:
                        # 插件已存在或压缩已开启
                        pass
                    except Exception as inner_e:
                        if "already a hypertable" in str(inner_e).lower() or "already exists" in str(inner_e).lower():
                            pass
                        else:
                            logger.warning(f"⚠️ SQL 执行警告或跳过: {inner_e}")

        logger.info("🎉 升维完毕！您的普通关系引擎已成功进化为超级时序数据库 (TimescaleDB)！")
    except Exception as e:
        logger.error(f"❌ 初始化 TimescaleDB 核心失败: {e}")

if __name__ == "__main__":
    migrate_to_timescaledb()
