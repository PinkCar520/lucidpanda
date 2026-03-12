import os
import redis
import psycopg2
from src.alphasignal.config import settings

def check_postgres():
    print("--- Checking PostgreSQL ---")
    # Try docker-compose defaults first
    creds = [
        {"user": "alphasignal", "pass": "secure_password", "db": "alphasignal_core"},
        {"user": "postgres", "pass": "postgres", "db": "alphasignal"}
    ]
    
    for cred in creds:
        try:
            conn = psycopg2.connect(
                host="localhost",
                port="5432",
                user=cred["user"],
                password=cred["pass"],
                dbname=cred["db"],
                connect_timeout=3
            )
            cursor = conn.cursor()
            
            cursor.execute("SELECT count(*) FROM fund_holdings;")
            holdings_count = cursor.fetchone()[0]
            print(f"Success with {cred['user']}@{cred['db']}")
            print(f"fund_holdings count: {holdings_count}")
            
            cursor.execute("SELECT count(*) FROM fund_valuation;")
            valuation_count = cursor.fetchone()[0]
            print(f"fund_valuation count: {valuation_count}")
            
            conn.close()
            return
        except Exception as e:
            print(f"Attempt with {cred['user']} failed: {e}")

def check_redis():
    print("\n--- Checking Redis ---")
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        keys = r.keys("fund:*")
        print(f"Total keys starting with 'fund:': {len(keys)}")
        if keys:
            print("Sample keys:")
            for k in keys[:5]:
                print(f"  - {k}")
    except Exception as e:
        print(f"Redis connection failed: {e}")

if __name__ == "__main__":
    check_postgres()
    check_redis()
