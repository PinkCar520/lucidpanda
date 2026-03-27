# ruff: noqa
import os
import sqlite3
import unittest.mock as mock
from datetime import date, datetime, timezone

# Aggressive global mocking for environment without Postgres
mock.patch("psycopg.connect").start()
mock.patch("psycopg_pool.ConnectionPool").start()
# Mock database_poller which starts a thread/loop
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import INET, JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.types import JSON, TEXT
from sqlalchemy import event, Engine
import uuid

from src.lucidpanda.auth.models import Base
from src.lucidpanda.config import settings
from sqlmodel import SQLModel

TEST_USER_ID = "408ba5ca-598d-4ee8-a5be-4352ab5f7918"


def _adapt_datetime_sqlite(value: datetime) -> str:
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat(sep=" ")


def _adapt_date_sqlite(value: date) -> str:
    return value.isoformat()


sqlite3.register_adapter(datetime, _adapt_datetime_sqlite)
sqlite3.register_adapter(date, _adapt_date_sqlite)


@compiles(INET, "sqlite")
def compile_inet_sqlite(_type, _compiler, **_kw) -> str:
    return "TEXT"


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(_type, _compiler, **_kw) -> str:
    return "JSON"


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if str(dbapi_connection.__class__).find("sqlite") != -1:
        dbapi_connection.create_function("gen_random_uuid", 0, lambda: str(uuid.uuid4()))
        
        # Custom JSON_AGG for SQLite
        import json
        class JsonAgg:
            def __init__(self):
                self.items = []
            def step(self, value):
                if value is not None:
                    try:
                        self.items.append(json.loads(value))
                    except (ValueError, TypeError):
                        self.items.append(value)
            def finalize(self):
                return json.dumps(self.items)

        dbapi_connection.create_aggregate("jsonb_agg", 1, JsonAgg)
        
        def sqlite_date_trunc(unit, ts_str):
            if not ts_str: return None
            # Handle both ISO and SQLite space format
            ts_str = ts_str.replace('T', ' ')
            if unit == 'hour':
                return ts_str[:13] + ":00:00"
            if unit == 'day':
                return ts_str[:10] + " 00:00:00"
            return ts_str
            
        dbapi_connection.create_function("date_trunc", 2, sqlite_date_trunc)
        # Set datetime format to match ISO for easier comparison
        dbapi_connection.execute("PRAGMA date_class = 'text'")


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
    
    if test_db_url.startswith("sqlite"):
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS fund_watchlist (
                    id TEXT DEFAULT (gen_random_uuid()),
                    user_id TEXT,
                    fund_code TEXT,
                    fund_name TEXT,
                    group_id TEXT,
                    sort_index INTEGER DEFAULT 0,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, fund_code)
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS watchlist_groups (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    name TEXT,
                    icon TEXT,
                    color TEXT,
                    sort_index INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS watchlist_sync_log (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    operation_type TEXT,
                    fund_code TEXT,
                    old_value TEXT,
                    new_value TEXT,
                    device_id TEXT,
                    client_timestamp TIMESTAMP,
                    is_synced BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            conn.commit()

    Base.metadata.create_all(bind=engine)
    SQLModel.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def db_session(db_engine):
    from sqlmodel import Session
    session = Session(db_engine)
    yield session
    # Cleanup after each test
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()


@pytest.fixture(autouse=True)
def override_api_session(db_session):
    from scripts.core.sse_server import app
    from src.lucidpanda.infra.database.connection import get_session
    
    def _override():
        yield db_session
        
    app.dependency_overrides[get_session] = _override
    yield
    app.dependency_overrides.pop(get_session, None)


@pytest.fixture(autouse=True)
def override_api_auth():
    from scripts.core.sse_server import app
    from src.lucidpanda.auth.dependencies import get_current_user
    
    class MockUser:
        def __init__(self):
            self.id = TEST_USER_ID
            self.username = "testuser"
            
    def _override():
        return MockUser()
        
    app.dependency_overrides[get_current_user] = _override
    yield
    app.dependency_overrides.pop(get_current_user, None)
