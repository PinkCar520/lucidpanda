#!/usr/bin/env python3
import sqlite3
import os
import json
import logging
import sys
from datetime import datetime
import pytz

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Requirements check
try:
    import psycopg2
    from psycopg2.extras import Json
except ImportError:
    logger.error("❌ 'psycopg2-binary' is required. Run: pip install psycopg2-binary")
    sys.exit(1)

# Configuration from Env or Defaults
SQLITE_DB_PATH = os.getenv("DB_PATH", "alphasignal.db")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = os.getenv("POSTGRES_PORT", "5432")
PG_USER = os.getenv("POSTGRES_USER", "alphasignal")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "secure_password")
PG_DB   = os.getenv("POSTGRES_DB", "alphasignal_core")

def get_sqlite_conn():
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"❌ SQLite database not found at: {SQLITE_DB_PATH}")
        sys.exit(1)
    return sqlite3.connect(SQLITE_DB_PATH)

def get_pg_conn():
    try:
        conn = psycopg2.connect(
            host=PG_HOST,
            port=PG_PORT,
            user=PG_USER,
            password=PG_PASSWORD,
            dbname=PG_DB
        )
        return conn
    except Exception as e:
        logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
        sys.exit(1)

def create_pg_table(cursor):
    """Creates the table schema if it doesn't exist."""
    logger.info("🔨 Creating PostgreSQL schema...")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS intelligence (
            id SERIAL PRIMARY KEY,
            timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
            source_id TEXT UNIQUE,
            author TEXT,
            content TEXT,
            
            -- JSONB Fields
            summary JSONB,
            sentiment JSONB,
            market_implication JSONB,
            actionable_advice JSONB,
            
            urgency_score INTEGER,
            url TEXT,
            
            -- Market Data
            gold_price_snapshot DOUBLE PRECISION,
            price_1h DOUBLE PRECISION,
            price_24h DOUBLE PRECISION
        );
        
        CREATE INDEX IF NOT EXISTS idx_intelligence_timestamp ON intelligence(timestamp DESC);
        CREATE INDEX IF NOT EXISTS idx_intelligence_source_id ON intelligence(source_id);
    """)

def parse_json_safely(value):
    """Parses JSON string to dict, or returns original value/default if failed."""
    if not value:
        return {}
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except:
        # If it's a plain string, wrap it in our i18n structure or just return as is?
        # Better key it to 'en' or 'zh' generally, but simple structure is safer.
        # Fallback to simple object
        return {"raw": value}

def migrate_data():
    sqlite = get_sqlite_conn()
    sqlite.row_factory = sqlite3.Row
    pg_conn = get_pg_conn()
    
    try:
        cur_sqlite = sqlite.cursor()
        cur_pg = pg_conn.cursor()
        
        # 1. Ensure Schema
        create_pg_table(cur_pg)
        
        # 2. Fetch Data
        logger.info("📥 Reading data from SQLite...")
        cur_sqlite.execute("SELECT * FROM intelligence ORDER BY id ASC")
        rows = cur_sqlite.fetchall()
        logger.info(f"📊 Found {len(rows)} records to migrate.")
        
        if not rows:
            logger.info("⚠️ No data to migrate.")
            return

        # 3. Insert Data
        logger.info("🚀 Starting migration...")
        success_count = 0
        error_count = 0
        
        for row in rows:
            try:
                # Parse Timestamp
                # SQLite timestamp: "2024-01-30 12:00:00" or similar
                ts_str = row['timestamp']
                ts_dt = None
                if ts_str:
                    try:
                        # Try parsing with dateutil if available, simplified here
                        ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            ts_dt = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S.%f")
                        except:
                            pass
                
                # If naive, assume UTC or Local? Project seems to use UTC internally mostly.
                if ts_dt and not ts_dt.tzinfo:
                    ts_dt = pytz.utc.localize(ts_dt)

                # Prepare Data
                # Note: We manually insert 'id' to preserve history linkage
                cur_pg.execute("""
                    INSERT INTO intelligence (
                        id, timestamp, source_id, author, content,
                        summary, sentiment, market_implication, actionable_advice,
                        urgency_score, url,
                        gold_price_snapshot, price_1h, price_24h
                    ) VALUES (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s,
                        %s, %s, %s
                    )
                    ON CONFLICT (id) DO NOTHING;
                """, (
                    row['id'],
                    ts_dt or datetime.now(pytz.utc),
                    row['source_id'],
                    row['author'],
                    row['content'],
                    Json(parse_json_safely(row['summary'])),
                    Json(parse_json_safely(row['sentiment'])),
                    Json(parse_json_safely(row['market_implication'])),
                    Json(parse_json_safely(row['actionable_advice'])),
                    row['urgency_score'],
                    row['url'],
                    row['gold_price_snapshot'],
                    row['price_1h'],
                    row['price_24h']
                ))
                success_count += 1
                
                if success_count % 100 == 0:
                    logger.info(f"⏳ Migrated {success_count} records...")
                    
            except Exception as e:
                logger.error(f"❌ Error migrating row ID {row['id']}: {e}")
                error_count += 1
        
        # 4. Sync Sequence
        # Since we manually inserted IDs, we must reset the ID sequence
        logger.info("🔄 Syncing ID sequence...")
        cur_pg.execute("SELECT setval('intelligence_id_seq', (SELECT MAX(id) FROM intelligence));")
        
        pg_conn.commit()
        logger.info(f"✅ Migration Complete! Success: {success_count}, Errors: {error_count}")

    except Exception as e:
        logger.error(f"🚨 Critical Migration Error: {e}")
        pg_conn.rollback()
    finally:
        sqlite.close()
        pg_conn.close()

if __name__ == "__main__":
    migrate_data()
