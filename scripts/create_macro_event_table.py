from sqlmodel import SQLModel
from src.alphasignal.infra.database.connection import engine
from src.alphasignal.models.macro_event import MacroEvent
from src.alphasignal.core.logger import logger

def create_tables():
    logger.info("Creating MacroEvent table...")
    SQLModel.metadata.create_all(engine)
    logger.info("Table created successfully.")

if __name__ == "__main__":
    create_tables()
