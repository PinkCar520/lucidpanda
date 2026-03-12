#!/usr/bin/env python3
import sys
import os
from datetime import datetime

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

def migrate_advanced_metrics():
    db = IntelligenceDB()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    logger.info("🛠️ Starting advanced metrics migration (Clustering & Exhaustion)...")
    
    # Fetch all records
    cursor.execute("SELECT id, timestamp FROM intelligence")
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("✅ No records found.")
        return

    logger.info(f"📊 Found {len(rows)} records to update.")
    
    updated_count = 0
    for record_id, timestamp in rows:
        clustering, exhaustion = db.get_advanced_metrics(timestamp, "")
        cursor.execute("UPDATE intelligence SET clustering_score = %s, exhaustion_score = %s WHERE id = %s", 
                       (clustering, exhaustion, record_id))
        updated_count += 1
        
        if updated_count % 100 == 0:
            logger.info(f"🔄 Updated {updated_count}/{len(rows)}...")
            conn.commit()
            
    conn.commit()
    logger.info(f"✅ Migration complete. {updated_count} records updated.")
    conn.close()

if __name__ == "__main__":
    migrate_advanced_metrics()
