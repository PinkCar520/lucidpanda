import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import INET
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.lucidpanda.auth.models import Base
from src.lucidpanda.config import settings


@compiles(INET, "sqlite")
def compile_inet_sqlite(_type, _compiler, **_kw) -> str:
    return "TEXT"


@pytest.fixture(scope="session")
def db_engine():
    test_db_url = os.getenv("TEST_DATABASE_URL")
    if not test_db_url:
        db_name = os.getenv("POSTGRES_TEST_DB") or settings.POSTGRES_DB
        if db_name.endswith("_test"):
            test_db_url = (
                f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
                f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{db_name}"
            )
        else:
            test_db_url = "sqlite+pysqlite:///:memory:"

    engine_kwargs = {}
    if test_db_url.startswith("sqlite"):
        engine_kwargs = {
            "connect_args": {"check_same_thread": False},
            "poolclass": StaticPool,
        }

    engine = create_engine(test_db_url, **engine_kwargs)
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
