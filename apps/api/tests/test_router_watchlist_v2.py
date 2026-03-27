# ruff: noqa
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, text
from datetime import datetime, UTC, timedelta
import json
import unittest.mock as mock

# Mock database_poller before anything else
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

from scripts.core.sse_server import app

client = TestClient(app)

@pytest.fixture(name="session")
def session_fixture(db_session):
    # Ensure default group exists for the test user
    uid = "408ba5ca-598d-4ee8-a5be-4352ab5f7918"
    db_session.execute(text(f"INSERT OR IGNORE INTO watchlist_groups (id, user_id, name) VALUES ('default-id', '{uid}', '默认分组')"))
    db_session.commit()
    return db_session

BASE_URL = "/api/v1/web/watchlist"

def test_get_watchlist_groups(session: Session):
    response = client.get(f"{BASE_URL}/groups")
    assert response.status_code == 200
    assert "data" in response.json()

def test_create_and_delete_group(session: Session):
    # Create
    resp = client.post(f"{BASE_URL}/groups", json={"name": "Temp Group"})
    assert resp.status_code == 200
    group_id = resp.json()["data"]["id"]
    
    # Delete
    del_resp = client.delete(f"{BASE_URL}/groups/{group_id}")
    assert del_resp.status_code == 200
    assert del_resp.json()["success"] is True

def test_reorder_groups(session: Session):
    # Create two groups
    g1_resp = client.post(f"{BASE_URL}/groups", json={"name": "G1", "sort_index": 1})
    assert g1_resp.status_code == 200
    g1 = g1_resp.json()["data"]["id"]
    
    g2_resp = client.post(f"{BASE_URL}/groups", json={"name": "G2", "sort_index": 2})
    assert g2_resp.status_code == 200
    g2 = g2_resp.json()["data"]["id"]
    
    # Reorder
    reorder_data = {
        "items": [
            {"group_id": g1, "sort_index": 10},
            {"group_id": g2, "sort_index": 20}
        ],
        "client_updated_at": (datetime.now(UTC) + timedelta(minutes=1)).isoformat()
    }
    response = client.post(f"{BASE_URL}/groups/reorder", json=reorder_data)
    assert response.status_code == 200
    
    # Verify
    groups_resp = client.get(f"{BASE_URL}/groups")
    groups = groups_resp.json()["data"]
    match = [g for g in groups if g["id"] == g1]
    assert len(match) > 0
    assert match[0]["sort_index"] == 10

def test_sync_complex_operations(session: Session):
    # Sync ADD
    sync_data = {
        "operations": [
            {
                "operation_type": "ADD",
                "fund_code": "888888",
                "fund_name": "Sync Fund 1",
                "client_timestamp": datetime.now(UTC).isoformat()
            }
        ]
    }
    response = client.post(f"{BASE_URL}/sync", json=sync_data)
    assert response.status_code == 200
    
    # Verify Addition
    watchlist_resp = client.get(BASE_URL)
    watchlist = watchlist_resp.json()["data"]
    assert any(f["fund_code"] == "888888" for f in watchlist)

def test_batch_operations(session: Session):
    # Batch Add
    batch_add = {
        "items": [{"code": "111111", "name": "F1"}, {"code": "222222", "name": "F2"}]
    }
    client.post(f"{BASE_URL}/batch-add", json=batch_add)
    
    # Batch Delete
    batch_del = {"codes": ["111111"]}
    # Uses DELETE method on /api/v1/web/watchlist/batch
    response = client.request("DELETE", f"{BASE_URL}/batch", json=batch_del)
    assert response.status_code == 200
    
    # Verify
    watchlist = client.get(BASE_URL).json()["data"]
    codes = [f["fund_code"] for f in watchlist]
    assert "222222" in codes
    assert "111111" not in codes
