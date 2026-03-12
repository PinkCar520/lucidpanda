#!/usr/bin/env python3
import sys
import os
from datetime import datetime

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

def migrate_sessions():
    db = IntelligenceDB()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    logger.info("🛠️ Starting session migration for existing records...")
    
    # Fetch all records without market_session
    cursor.execute("SELECT id, timestamp FROM intelligence WHERE market_session IS NULL")
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("✅ No records need migration.")
        return

    logger.info(f"📊 Found {len(rows)} records to update.")
    
    updated_count = 0
    for record_id, timestamp in rows:
        session = db.get_market_session(timestamp)
        cursor.execute("UPDATE intelligence SET market_session = %s WHERE id = %s", (session, record_id))
        updated_count += 1
        
        if updated_count % 50 == 0:
            logger.info(f"🔄 Updated {updated_count}/{len(rows)}...")
            conn.commit()
            
    conn.commit()
    logger.info(f"✅ Migration complete. {updated_count} records updated.")
    conn.close()

if __name__ == "__main__":
    migrate_sessions()
