from sqlmodel import Session, text
from src.lucidpanda.infra.database.connection import engine
from src.lucidpanda.core.logger import logger

def migrate():
    logger.info("Adding 'category' column to intelligence table...")
    with Session(engine) as session:
        try:
            # Check if column exists first
            check_sql = text("SELECT column_name FROM information_schema.columns WHERE table_name='intelligence' AND column_name='category';")
            result = session.execute(check_sql).fetchone()
            
            if not result:
                # Add column
                session.execute(text("ALTER TABLE intelligence ADD COLUMN category VARCHAR(50) DEFAULT 'macro_gold';"))
                # Create index
                session.execute(text("CREATE INDEX ix_intelligence_category ON intelligence (category);"))
                session.commit()
                logger.info("Column 'category' added successfully.")
            else:
                logger.info("Column 'category' already exists.")
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            session.rollback()

if __name__ == "__main__":
    migrate()
