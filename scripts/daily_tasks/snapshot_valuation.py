
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
    T+0 15:05: Snapshot real-time valuations using the standard engine method.
    This ensures consistency with the automated scheduler and correct DB tables.
    """
    print(f"📸 Starting Daily Valuation Snapshot (Manual Trigger): {datetime.now()}")
    
    try:
        db = IntelligenceDB()
        engine = FundEngine(db=db)
        
        # Use the standard method that saves to 'fund_valuation_archive'
        engine.take_all_funds_snapshot()
        
        print(f"✅ Snapshot complete using standard engine logic.")
        
    except Exception as e:
        print(f"❌ Task Failed: {e}")

if __name__ == "__main__":
    daily_snapshot_task()
