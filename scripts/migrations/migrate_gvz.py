#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timedelta

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.import_trump_history import TrumpHistoryImporter
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

def migrate_gvz():
    importer = TrumpHistoryImporter()
    db = IntelligenceDB()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    logger.info("🛠️ Starting GVZ volatility data migration...")
    
    # Fetch all records without GVZ data
    cursor.execute("SELECT id, timestamp FROM intelligence WHERE gvz_snapshot IS NULL")
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("✅ No records need GVZ migration.")
        return

    logger.info(f"📊 Found {len(rows)} records to update.")
    
    # Group records by day to batch fetch
    records_by_day = {}
    for record_id, timestamp in rows:
        day = timestamp.date()
        if day not in records_by_day:
            records_by_day[day] = []
        records_by_day[day].append((record_id, timestamp))
    
    updated_count = 0
    for day, day_records in sorted(records_by_day.items()):
        logger.info(f"📅 Processing date: {day}")
        
        start_date = datetime.combine(day, datetime.min.time())
        end_date = datetime.combine(day, datetime.max.time())
        
        # Batch fetch GVZ
        gvz_df = importer.get_price_data_for_date_range(start_date, end_date, "^GVZ")
        
        for record_id, timestamp in day_records:
            # dummy other DFs
            _, _, _, _, _, gvz = importer.get_gold_price_at_time(
                timestamp.isoformat(), 
                price_df=gvz_df, # Hack: use gvz_df as price_df for index matching
                gvz_df=gvz_df
            )
            
            cursor.execute("""
                UPDATE intelligence 
                SET gvz_snapshot = %s 
                WHERE id = %s
            """, (gvz, record_id))
            updated_count += 1
            
        logger.info(f"🔄 Progress: {updated_count}/{len(rows)}...")
        conn.commit()
            
    conn.commit()
    logger.info(f"✅ Migration complete. {updated_count} records updated.")
    conn.close()

if __name__ == "__main__":
    migrate_gvz()
