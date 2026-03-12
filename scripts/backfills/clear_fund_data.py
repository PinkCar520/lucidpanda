import os
import redis
import psycopg2
from src.alphasignal.config import settings

def clear_postgres():
    print("--- Clearing PostgreSQL Valuation History ---")
    try:
        conn = psycopg2.connect(
            host="localhost",
            port="5432",
            user="alphasignal",
            password="secure_password",
            dbname="alphasignal_core",
            connect_timeout=3
        )
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM fund_valuation;")
        deleted_count = cursor.rowcount
        print(f"Successfully deleted {deleted_count} records from fund_valuation.")
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"PostgreSQL clearing failed: {e}")

def clear_redis():
    print("\n--- Clearing Redis Fund Cache ---")
    try:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        r = redis.from_url(redis_url, decode_responses=True)
        keys = r.keys("fund:*")
        if keys:
            deleted_count = r.delete(*keys)
            print(f"Successfully deleted {deleted_count} keys from Redis.")
        else:
            print("No 'fund:*' keys found in Redis.")
    except Exception as e:
        print(f"Redis clearing failed: {e}")

if __name__ == "__main__":
    clear_postgres()
    clear_redis()
