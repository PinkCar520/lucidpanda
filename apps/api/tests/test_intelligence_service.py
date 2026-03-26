import unittest.mock
from unittest.mock import MagicMock, patch
import pytest
import time
from datetime import datetime, timezone
from sqlmodel import Session
from src.lucidpanda.services.intelligence_service import IntelligenceService
from src.lucidpanda.models.intelligence import Intelligence

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def intelligence_service(mock_db):
    # Mocking IntelligenceDB and redis to avoid external calls
    with patch("src.lucidpanda.services.intelligence_service.IntelligenceDB"), \
         patch("src.lucidpanda.services.intelligence_service.redis.from_url"):
        return IntelligenceService(mock_db)

def test_get_intelligence_full(intelligence_service, mock_db):
    # Mock return data
    mock_intelligence = Intelligence(
        id=1,
        content="Test News Content",
        timestamp=datetime.now(timezone.utc),
        corroboration_count=1,
        source_credibility_score=0.8,
        urgency_score=5
    )
    mock_db.exec.return_value.all.return_value = [mock_intelligence]
    
    results = intelligence_service.get_intelligence_full(limit=1)
    assert len(results) == 1
    assert results[0]["content"] == "Test News Content"
    assert "confidence_score" in results[0]
    assert "confidence_level" in results[0]

def test_get_fused_intelligence_cache_hit(intelligence_service):
    # Mock the cache store
    mock_cache = MagicMock()
    mock_cache.get.return_value = {"fused": "data"}
    intelligence_service._fused_cache_store = mock_cache
    
    result = intelligence_service.get_fused_intelligence(force_refresh=False)
    assert result == {"fused": "data"}
    mock_cache.get.assert_called_once()

def test_get_graph_quality(intelligence_service, mock_db):
    # Mock summary row
    mock_row = MagicMock()
    mock_row._mapping = {"completed_count": 100, "with_relations_count": 60}
    mock_db.execute.return_value.first.return_value = mock_row
    
    quality = intelligence_service.get_graph_quality()
    assert quality["summary"]["completed_count"] == 100
    assert "relation_coverage_pct" in quality["summary"]

def test_get_sources_dashboard(intelligence_service, mock_db):
    # Mock source stats return
    mock_row = MagicMock()
    mock_row._mapping = {"source_name": "Source A", "total_signals": 10, "last_seen": datetime.now(timezone.utc)}
    mock_db.execute.return_value.all.return_value = [mock_row]
    
    dashboard = intelligence_service.get_sources_dashboard()
    assert "leaderboard" in dashboard
    assert dashboard["leaderboard"][0]["source_name"] == "Source A"

def test_get_intelligence_item(intelligence_service, mock_db):
    mock_intelligence = Intelligence(id=1, content="Single Item Content")
    # mock_db.exec(...).first()
    mock_db.exec.return_value.first.return_value = mock_intelligence
    
    result = intelligence_service.get_intelligence_item(1)
    assert result["content"] == "Single Item Content"

@pytest.mark.anyio
async def test_get_fund_ai_analysis(intelligence_service, mock_db):
    # Mock complex SQL execution
    mock_db.execute.return_value.mappings.return_value.all.return_value = [
        {
            "id": 1, 
            "timestamp": datetime.now(timezone.utc), 
            "summary": {"zh": "Fund Event Summary"},
            "sentiment_score": 0.5,
            "author": "System",
            "urgency_score": 8,
            "actionable_advice": None
        }
    ]
    
    # Mock cache and market service inside the call if needed
    with patch("src.lucidpanda.infra.cache.get_cached", return_value=None), \
         patch("src.lucidpanda.infra.cache.set_cached"):
        analysis = await intelligence_service.get_fund_ai_analysis("user1", "600519", "Moutai")
        assert analysis["fund_code"] == "600519"
        assert len(analysis["related_intelligence"]) == 1
        assert analysis["related_intelligence"][0]["summary"] == "Fund Event Summary"
