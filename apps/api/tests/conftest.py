import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.lucidpanda.auth.models import Base
from src.lucidpanda.config import settings

@pytest.fixture(scope="session")
def db_engine():
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        db_name = os.getenv("POSTGRES_TEST_DB") or settings.POSTGRES_DB
        if not db_name.endswith("_test"):
            raise RuntimeError(
                "Refusing to run tests against a non-test database. "
                "Set TEST_DATABASE_URL or POSTGRES_TEST_DB with a *_test database name."
            )
        test_db_url = (
            f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
            f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
        )

    engine = create_engine(test_db_url)
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def db_session(db_engine):
    Session = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = Session()
    yield session
    # Cleanup after each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()
