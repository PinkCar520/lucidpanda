# ruff: noqa
import unittest.mock as mock
import pytest  # noqa: F401
import os
from fastapi.testclient import TestClient
from datetime import datetime, timedelta  # noqa: F401
from sqlalchemy import inspect, StaticPool

# 1. Aggressive global mocking BEFORE any other imports
# Mock database_poller to avoid the long-running task in sse_server
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

# 2. Now import the rest
from scripts.core.sse_server import app  # noqa: E402
from src.lucidpanda.infra.database.connection import get_session  # noqa: E402
from src.lucidpanda.models.intelligence import Intelligence  # noqa: E402, F401
from sqlmodel import Session, create_engine, SQLModel  # noqa: E402

client = TestClient(app)

@pytest.fixture(name="session")
def session_fixture(db_session):
    return db_session

@pytest.fixture(autouse=True, scope="module")
def cleanup_after_all_tests():
    yield
    # if os.path.exists(db_file):
    #     os.remove(db_file)

def test_get_24h_alerts_count_empty(session: Session):
    print("DEBUG: Running test_get_24h_alerts_count_empty")
    response = client.get("/api/v1/alerts/24h")
    assert response.status_code == 200
    assert response.json() == {"count": 0}
