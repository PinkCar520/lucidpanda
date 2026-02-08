import sys
import os

# Add the project root to sys.path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine, inspect, text
from src.alphasignal.config import settings
from src.alphasignal.auth.models import Base

def get_engine():
    print(f"DEBUG: settings.DB_TYPE = {settings.DB_TYPE}")
    if settings.DB_TYPE == "sqlite":
        os.makedirs(os.path.dirname(settings.DB_PATH), exist_ok=True)
        db_url = f"sqlite:///{settings.DB_PATH}"
    else:
        db_url = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    
    print(f"DEBUG: Connecting to {db_url}")
    return create_engine(db_url)

def migrate():
    engine = get_engine()
    inspector = inspect(engine)
    
    print(f"Migrating database: {settings.DB_TYPE}...")

    # Create new tables
    print("Creating new tables (if not exist)...")
    Base.metadata.create_all(engine)
    
    with engine.connect() as conn:
        # --- Users Table ---
        if inspector.has_table("users"):
            columns = [c['name'] for c in inspector.get_columns('users')]
            
            # Rename full_name -> name
            if 'full_name' in columns and 'name' not in columns:
                print("Renaming 'full_name' to 'name' in 'users' table...")
                try:
                    conn.execute(text("ALTER TABLE users RENAME COLUMN full_name TO name"))
                except Exception as e:
                    print(f"Warning: Could not rename 'full_name' to 'name': {e}")
            
            # Add new columns
            new_user_cols = {
                'avatar_url': 'VARCHAR(255)',
                'nickname': 'VARCHAR(100)',
                'gender': 'VARCHAR(20)',
                'birthday': 'DATE',
                'location': 'VARCHAR(255)',
                'language_preference': "VARCHAR(10) DEFAULT 'en'",
                'timezone': "VARCHAR(50) DEFAULT 'UTC'",
                'theme_preference': "VARCHAR(20) DEFAULT 'system'",
                'phone_number': 'VARCHAR(20)',
                'is_phone_verified': 'BOOLEAN DEFAULT 0' if settings.DB_TYPE == 'sqlite' else 'BOOLEAN DEFAULT FALSE',
                'two_fa_secret': 'VARCHAR(255)',
                'is_two_fa_enabled': 'BOOLEAN DEFAULT 0' if settings.DB_TYPE == 'sqlite' else 'BOOLEAN DEFAULT FALSE'
            }
            
            for col, type_ in new_user_cols.items():
                if col not in columns:
                    print(f"Adding column '{col}' to 'users' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {type_}"))
                    except Exception as e:
                        print(f"Error adding column {col}: {e}")

        # --- RefreshTokens Table ---
        if inspector.has_table("refresh_tokens"):
            rt_columns = [c['name'] for c in inspector.get_columns('refresh_tokens')]
            new_rt_cols = {
                'device_info': 'TEXT' if settings.DB_TYPE == 'sqlite' else 'JSONB',
                'user_agent': 'TEXT',
                'last_active_at': 'TIMESTAMP'
            }
            for col, type_ in new_rt_cols.items():
                if col not in rt_columns:
                    print(f"Adding column '{col}' to 'refresh_tokens' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE refresh_tokens ADD COLUMN {col} {type_}"))
                    except Exception as e:
                        print(f"Error adding column {col}: {e}")

        # --- EmailChangeRequests Table ---
        if inspector.has_table("email_change_requests"):
            ecr_columns = [c['name'] for c in inspector.get_columns('email_change_requests')]
            new_ecr_cols = {
                'old_email': 'VARCHAR(255)',
                'old_email_token_hash': 'VARCHAR(255)',
                'new_email_token_hash': 'VARCHAR(255)',
                'old_email_verified_at': 'TIMESTAMP',
                'new_email_verified_at': 'TIMESTAMP',
                'is_completed': 'BOOLEAN DEFAULT 0' if settings.DB_TYPE == 'sqlite' else 'BOOLEAN DEFAULT FALSE',
                'is_cancelled': 'BOOLEAN DEFAULT 0' if settings.DB_TYPE == 'sqlite' else 'BOOLEAN DEFAULT FALSE'
            }
            for col, type_ in new_ecr_cols.items():
                if col not in ecr_columns:
                    print(f"Adding column '{col}' to 'email_change_requests' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE email_change_requests ADD COLUMN {col} {type_}"))
                    except Exception as e:
                        print(f"Error adding column {col}: {e}")

        conn.commit()
        print("Migration complete.")

if __name__ == "__main__":
    migrate()
