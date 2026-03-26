from sqlmodel import SQLModel
from src.lucidpanda.core.logger import logger
from src.lucidpanda.infra.database.connection import engine


def create_tables():
    logger.info("Creating MacroEvent table...")
    SQLModel.metadata.create_all(engine)
    logger.info("Table created successfully.")

if __name__ == "__main__":
    create_tables()
