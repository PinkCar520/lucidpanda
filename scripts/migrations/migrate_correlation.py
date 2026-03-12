#!/usr/bin/env python3
import sys
import os
from datetime import datetime, timedelta

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.import_trump_history import TrumpHistoryImporter
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

def migrate_correlation():
    importer = TrumpHistoryImporter()
    db = IntelligenceDB()
    conn = db._get_conn()
    cursor = conn.cursor()
    
    logger.info("🛠️ Starting correlation data migration (DXY & US10Y)...")
    
    # Fetch all records without correlation data
    cursor.execute("SELECT id, timestamp FROM intelligence WHERE dxy_snapshot IS NULL OR us10y_snapshot IS NULL")
    rows = cursor.fetchall()
    
    if not rows:
        logger.info("✅ No records need correlation migration.")
        return

    logger.info(f"📊 Found {len(rows)} records to update.")
    
    # Group records by day to batch fetch price data
    records_by_day = {}
    for record_id, timestamp in rows:
        day = timestamp.date()
        if day not in records_by_day:
            records_by_day[day] = []
        records_by_day[day].append((record_id, timestamp))
    
    updated_count = 0
    for day, day_records in sorted(records_by_day.items()):
        logger.info(f"📅 Processing date: {day}")
        
        # Batch fetch for the day
        start_date = datetime.combine(day, datetime.min.time())
        end_date = datetime.combine(day, datetime.max.time())
        
        # We use TrumpHistoryImporter's internal cache
        dxy_df = importer.get_price_data_for_date_range(start_date, end_date, "DX-Y.NYB")
        us10y_df = importer.get_price_data_for_date_range(start_date, end_date, "^TNX")
        
        for record_id, timestamp in day_records:
            # We use a dummy price_df since we only care about correlation
            _, _, _, dxy, us10y = importer.get_gold_price_at_time(
                timestamp.isoformat(), 
                price_df=dxy_df, # Hack: use dxy_df as price_df just to satisfy indexing logic if needed
                dxy_df=dxy_df, 
                us10y_df=us10y_df
            )
            
            cursor.execute("""
                UPDATE intelligence 
                SET dxy_snapshot = %s, us10y_snapshot = %s 
                WHERE id = %s
            """, (dxy, us10y, record_id))
            updated_count += 1
            
        logger.info(f"🔄 Progress: {updated_count}/{len(rows)}...")
        conn.commit()
            
    conn.commit()
    logger.info(f"✅ Migration complete. {updated_count} records updated.")
    conn.close()

if __name__ == "__main__":
    migrate_correlation()
