#!/usr/bin/env python3
import os
import sys
import psycopg
from psycopg.rows import dict_row

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger

def fix_schema():
    logger.info("🛠️ Starting Fund Search Schema Fix...")
    
    conn_str = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    
    try:
        with psycopg.connect(conn_str, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                # 1. Fix fund_metadata
                logger.info("Checking fund_metadata columns...")
                cursor.execute("ALTER TABLE fund_metadata ADD COLUMN IF NOT EXISTS pinyin_full VARCHAR(255);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_fund_pinyin_full ON fund_metadata (pinyin_full);")
                
                # 2. Fix stock_metadata
                logger.info("Checking stock_metadata columns...")
                cursor.execute("ALTER TABLE stock_metadata ADD COLUMN IF NOT EXISTS pinyin_shorthand VARCHAR(50);")
                cursor.execute("ALTER TABLE stock_metadata ADD COLUMN IF NOT EXISTS pinyin_full VARCHAR(255);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_stock_pinyin ON stock_metadata (pinyin_shorthand);")
                
                conn.commit()
                logger.info("✅ Database schema updated successfully.")
                
    except Exception as e:
        logger.error(f"❌ Failed to fix schema: {e}")
        sys.exit(1)

if __name__ == "__main__":
    fix_schema()
