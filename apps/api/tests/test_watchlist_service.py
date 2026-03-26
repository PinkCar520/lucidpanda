import unittest.mock
from unittest.mock import MagicMock, patch
import pytest
from sqlmodel import Session
from src.lucidpanda.services.watchlist_service import WatchlistService

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def watchlist_service(mock_db):
    return WatchlistService(mock_db)

def test_get_groups(watchlist_service, mock_db):
    # Setup mock return
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {"id": "uuid1", "user_id": "user1", "name": "Group 1", "sort_index": 0}
    ]
    
    groups = watchlist_service.get_groups("user1")
    assert len(groups) == 1
    assert groups[0]["name"] == "Group 1"
    mock_db.execute.assert_called_once()

def test_create_group(watchlist_service, mock_db):
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "id": "new-uuid", "name": "New Group", "icon": "star", "color": "blue", "sort_index": 1
    }
    
    group = watchlist_service.create_group("user1", "New Group", "star", "blue", 1)
    assert group["id"] == "new-uuid"
    assert "INSERT INTO watchlist_groups" in str(mock_db.execute.call_args[0][0])

def test_update_group(watchlist_service, mock_db):
    mock_db.execute.return_value.mappings.return_value.first.return_value = {
        "id": "uuid", "name": "Updated"
    }
    
    result = watchlist_service.update_group("user1", "uuid", {"name": "Updated"})
    assert result["name"] == "Updated"
    assert "UPDATE watchlist_groups" in str(mock_db.execute.call_args[0][0])

def test_delete_group(watchlist_service, mock_db):
    # Mock finding default group
    mock_db.execute.return_value.first.return_value = MagicMock(id="default-id")
    
    success = watchlist_service.delete_group("user1", "old-id")
    assert success is True
    assert mock_db.execute.call_count >= 2 # Once for find default, once for move, once for delete

def test_reorder_groups(watchlist_service, mock_db):
    success = watchlist_service.reorder_groups("user1", [{"group_id": "g1", "sort_index": 0}])
    assert success is True
    assert mock_db.commit.called
    assert "UPDATE watchlist_groups" in str(mock_db.execute.call_args[0][0])

def test_batch_add(watchlist_service, mock_db):
    mock_db.execute.return_value.scalar.return_value = 5 # current max index
    mock_db.execute.return_value.mappings.return_value.first.return_value = {"id": "new-item-id"}
    
    results = watchlist_service.batch_add("user1", [{"code": "000001", "name": "Test"}])
    assert len(results) == 1
    assert results[0]["success"] is True

def test_sync_watchlist(watchlist_service, mock_db):
    mock_db.execute.return_value.mappings.return_value.all.return_value = []
    
    result = watchlist_service.sync_watchlist("user1")
    assert "data" in result
    assert "groups" in result
    assert "sync_time" in result
