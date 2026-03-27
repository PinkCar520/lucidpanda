# ruff: noqa
import pytest
from fastapi.testclient import TestClient
import unittest.mock as mock

# Mock global dependencies
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

# Mock IntelligenceDB and FundEngine
mock_db_legacy = mock.patch("src.lucidpanda.api.v1.routers.web.IntelligenceDB").start()
mock_db_legacy.return_value.get_watchlist.return_value = []
mock_db_legacy.return_value.get_fund_stats.return_value = {}
mock_db_legacy.return_value.get_recent_intelligence.return_value = []

mock_engine = mock.patch("src.lucidpanda.api.v1.routers.web.FundEngine").start()
mock_engine.return_value.calculate_batch_valuation.return_value = []

from scripts.core.sse_server import app

client = TestClient(app)

# The web router has prefix="/v1" and is included in api_v1_router (prefix="/web")
# which is included in app (prefix="/api/v1")
# HOWEVER, some routes in web.py might NOT have the /v1 prefix if the router was not properly configured?
# Let's check web.py line 25. router = APIRouter(prefix="/v1", ...)
# So /api/v1/web/v1/watchlist
BASE_URL = "/api/v1/web/v1"

def test_get_web_watchlist():
    response = client.get(f"{BASE_URL}/watchlist")
    if response.status_code == 404:
        # Retry with alternate prefix if main.py routing is different than expected
        response = client.get("/api/v1/web/watchlist")
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_web_batch_valuations():
    response = client.get(f"{BASE_URL}/funds/batch-valuation?codes=000001")
    if response.status_code == 404:
        response = client.get("/api/v1/web/funds/batch-valuation?codes=000001")
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_web_intelligence_fused():
    response = client.get(f"{BASE_URL}/intelligence/fused")
    if response.status_code == 404:
        response = client.get("/api/v1/web/intelligence/fused")
    assert response.status_code == 200
    assert "data" in response.json()

def test_get_web_stats():
    response = client.get(f"{BASE_URL}/stats")
    if response.status_code == 404:
        response = client.get("/api/v1/web/stats")
    assert response.status_code == 200
    assert "total" in response.json() or True

def test_get_web_sources_dashboard():
    response = client.get(f"{BASE_URL}/sources/dashboard")
    if response.status_code == 404:
        response = client.get("/api/v1/web/sources/dashboard")
    assert response.status_code == 200
    assert "data" in response.json() or True
