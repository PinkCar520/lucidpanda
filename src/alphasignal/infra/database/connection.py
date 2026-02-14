from sqlmodel import create_engine, Session
from src.alphasignal.config import settings

# Production-grade database connection management
# Using SQLModel (SQLAlchemy 2.0 compatible)

DATABASE_URL = f"postgresql://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"

# pool_size and max_overflow are crucial for production high-concurrency
engine = create_engine(
    DATABASE_URL,
    echo=False,  # Set to True only for deep debugging
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True  # Ensure connections are alive before using them
)

def get_session():
    with Session(engine) as session:
        yield session
