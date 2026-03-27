# ruff: noqa
import unittest.mock as mock
import pytest  # noqa: F401
from fastapi.testclient import TestClient

# 1. Aggressive global mocking BEFORE any other imports
mock_sqlalchemy = mock.patch("sqlalchemy.create_engine")
mock_psycopg = mock.patch("psycopg.connect")
mock_psycopg_pool = mock.patch("psycopg_pool.ConnectionPool")

mock_sqlalchemy.start()
mock_psycopg.start()
mock_psycopg_pool.start()

# Mock JSONB and INET for SQLite compatibility
import sqlalchemy  # noqa: E402, F401
from sqlalchemy.types import JSON, String  # noqa: E402
mock.patch("sqlalchemy.dialects.postgresql.JSONB", JSON).start()
mock.patch("sqlalchemy.dialects.postgresql.INET", String).start()

# Mock database_poller to avoid Redis/Postgres connections
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

# 2. Mock FactorService using AsyncMock for async methods
mock_factor_service = mock.MagicMock()
mock_factor_service.get_entity_trend_async = mock.AsyncMock()
mock_factor_service.get_top_hotspots_async = mock.AsyncMock()

# 3. Now import the app and inject the mock directly into the router
from scripts.core.sse_server import app  # noqa: E402
import src.lucidpanda.api.v1.routers.analytics as analytics_router  # noqa: E402
analytics_router.factor_service = mock_factor_service

client = TestClient(app)

def test_debug_print_routes():
    print("\n--- Registered Routes ---")
    for route in app.routes:
        if hasattr(route, "path"):
            print(f"Path: {route.path}")
    print("------------------------")

def test_get_entity_trend_success():
    # Setup mock data
    mock_factor_service.get_entity_trend_async.return_value = [
        {
            "metric_date": "2024-01-01",
            "avg_sentiment": 0.5,
            "mention_count": 10,
            "display_name": "Test Entity",
            "entity_type": "Organization"
        }
    ]
    
    response = client.get("/api/v1/analytics/pulse/trend/test_id?days=7")
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_id"] == "test_id"
    assert data["display_name"] == "Test Entity"
    assert len(data["trend"]) == 1
    assert data["trend"][0]["mention_count"] == 10

def test_get_entity_trend_not_found():
    mock_factor_service.get_entity_trend_async.return_value = []
    
    response = client.get("/api/v1/analytics/pulse/trend/unknown_id")
    assert response.status_code == 200
    data = response.json()
    assert data["canonical_id"] == "unknown_id"
    assert data["trend"] == []
    assert "No data found" in data["message"]

def test_get_hotspots_success():
    mock_factor_service.get_top_hotspots_async.return_value = [
        {"canonical_id": "id1", "display_name": "Hot 1", "mentions": 100},
        {"canonical_id": "id2", "display_name": "Hot 2", "mentions": 80}
    ]
    
    response = client.get("/api/v1/analytics/pulse/hotspots?days=1&limit=2")
    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["hotspots"][0]["display_name"] == "Hot 1"

def test_get_hotspots_error():
    mock_factor_service.get_top_hotspots_async.side_effect = Exception("Service failure")
    
    response = client.get("/api/v1/analytics/pulse/hotspots")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"
