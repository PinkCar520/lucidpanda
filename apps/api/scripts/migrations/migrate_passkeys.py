import os
import sys

import psycopg
from src.lucidpanda.config import settings


def migrate():
    print("🚀 Starting WebAuthn Database Migration...")

    conn = psycopg.connect(row_factory=__import__('psycopg.rows', fromlist=['dict_row']).dict_row,
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        dbname=settings.POSTGRES_DB
    )
    cursor = conn.cursor()

    try:
        # Create user_passkeys table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_passkeys (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                credential_id VARCHAR(512) UNIQUE NOT NULL,
                public_key TEXT NOT NULL,
                sign_count INTEGER NOT NULL DEFAULT 0,
                name VARCHAR(100),
                transports JSONB,
                created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                last_used_at TIMESTAMPTZ
            );
            CREATE INDEX IF NOT EXISTS idx_passkeys_credential_id ON user_passkeys(credential_id);
            CREATE INDEX IF NOT EXISTS idx_passkeys_user_id ON user_passkeys(user_id);
        """)

        conn.commit()
        print("✅ user_passkeys table created successfully.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    # Add root to sys.path to allow imports
    sys.path.append(os.getcwd())
    migrate()
