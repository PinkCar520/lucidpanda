import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from src.alphasignal.core.database import IntelligenceDB

db = IntelligenceDB()
conn = db.get_connection()
with conn.cursor() as cursor:
    cursor.execute("SELECT COUNT(*) FROM stock_metadata;")
    count = cursor.fetchone()[0]
    print(f"Stock Metadata Count: {count}")
    
    cursor.execute("SELECT * FROM industry_definitions LIMIT 5;")
    rows = cursor.fetchall()
    print("Sample Industries:")
    for r in rows:
        print(r)

conn.close()
