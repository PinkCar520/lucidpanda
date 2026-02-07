
import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime

# Set DB Credentials from environment or defaults
from src.alphasignal.config import settings

# Add src to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.fund_engine import FundEngine

def daily_snapshot_task():
    """
    T+0 15:05: Snapshot real-time valuations for all watched funds.
    """
    print(f"📸 Starting Daily Valuation Snapshot: {datetime.now()}")
    
    db = IntelligenceDB()
    engine = FundEngine(db=db)
    
    # 1. Get ALL unique funds from watchlists
    # Assuming standard table, execute raw SQL if method missing or use get_watchlist
    # We want ALL unique funds across all users to process efficiently
    conn = db.get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT fund_code FROM fund_watchlist")
        rows = cur.fetchall()
        fund_codes = [r[0] for r in rows]
        
        print(f"📋 Found {len(fund_codes)} distinct funds to snapshot.")
        
        # 2. Batch Calculate
        # This will use the current 'calibration' adjustments we hardcoded in engine
        # In future, it will use DB-stored adjustments
        results = engine.calculate_batch_valuation(fund_codes)
        
        # 3. Save to History Table (Need to create it first, but script can be pre-emptive)
        today = datetime.now().date()
        
        # Ensure table exists (Idempotent)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS fund_valuation_history (
                id SERIAL PRIMARY KEY,
                fund_code VARCHAR(10),
                valuation_date DATE,
                estimated_growth FLOAT,
                data_source VARCHAR(50),
                official_growth FLOAT,
                calibration_factor FLOAT DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(fund_code, valuation_date)
            );
        """)
        conn.commit()
        
        success_count = 0
        for res in results:
            if "error" in res: continue
            
            f_code = res['fund_code']
            est = res['estimated_growth']
            source = res.get('source', 'Unknown')
            
            # Extract calibration factor from source string if present
            # e.g. "EastMoney Batch (Incl. Calibration +0.65%)"
            calib = 0.0
            if "Calibration" in source and "+" in source:
                try:
                    part = source.split('+')[1].split('%')[0]
                    calib = float(part)
                except:
                    pass
            elif "Calibration" in source and "-" in source:
                 try:
                    part = source.split('Calibration')[1].split('%')[0].strip() # "-0.71"
                    calib = float(part)
                 except: pass

            try:
                cur.execute("""
                    INSERT INTO fund_valuation_history (fund_code, valuation_date, estimated_growth, data_source, calibration_factor)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (fund_code, valuation_date) 
                    DO UPDATE SET estimated_growth = EXCLUDED.estimated_growth, 
                                  data_source = EXCLUDED.data_source,
                                  calibration_factor = EXCLUDED.calibration_factor;
                """, (f_code, today, est, source, calib))
                success_count += 1
            except Exception as e:
                print(f"Failed to save {f_code}: {e}")
                conn.rollback() 
                continue

        conn.commit()
        print(f"✅ Snapshot complete. Saved {success_count}/{len(fund_codes)} records.")
        
    except Exception as e:
        print(f"❌ Task Failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    daily_snapshot_task()
