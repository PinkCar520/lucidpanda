import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.alphasignal.auth.models import Base

@pytest.fixture(scope="session")
def db_engine():
    # Use SQLite in-memory for fast unit tests
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
