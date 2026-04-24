"""
Migration: Add image_url to intelligence table
Date: 2026-04-24
"""
from src.lucidpanda.infra.database.connection import get_session
from sqlalchemy import text
from sqlmodel import Session

def migrate():
    print("🚀 Starting migration: add image_url to intelligence...")
    
    with Session(get_session().bind) as session:
        try:
            # 1. 检查列是否存在
            check_sql = text("""
                SELECT COUNT(*) 
                FROM information_schema.columns 
                WHERE table_name='intelligence' AND column_name='image_url';
            """)
            exists = session.execute(check_sql).scalar()
            
            if not exists:
                # 2. 增加列
                print("📝 Adding 'image_url' column to 'intelligence' table...")
                session.execute(text("ALTER TABLE intelligence ADD COLUMN image_url VARCHAR;"))
                session.commit()
                print("✅ Column added successfully.")
            else:
                print("ℹ️ Column 'image_url' already exists, skipping.")
                
        except Exception as e:
            session.rollback()
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate()
