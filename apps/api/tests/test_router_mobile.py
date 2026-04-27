# ruff: noqa
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, text
from datetime import UTC, datetime, timedelta
import unittest.mock as mock

# Mock database_poller before anything else
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

# Mock cache to always bypass for tests
mock.patch("src.lucidpanda.api.v1.routers.mobile.get_cached", return_value=None).start()
mock.patch("src.lucidpanda.api.v1.routers.mobile.set_cached", return_value=None).start()

# Mock market_terminal_service
mock_market = mock.patch("src.lucidpanda.api.v1.routers.mobile.market_terminal_service").start()
mock_market.get_market_snapshot.return_value = {
    "gold": {"price": 2150.5, "change": 1.2},
    "dxy": {"price": 103.5, "change": -0.1},
    "oil": {"price": 81.2, "change": 0.5},
    "us10y": {"price": 4.25, "change": 0.02}
}

from scripts.core.sse_server import app
from src.lucidpanda.models.intelligence import Intelligence

client = TestClient(app)

@pytest.fixture(name="session")
def session_fixture(db_session):
    return db_session

def test_get_mobile_intelligence_empty(session: Session):
    response = client.get("/api/v1/mobile/intelligence")
    assert response.status_code == 200
    assert response.json() == []

def test_get_mobile_intelligence_with_data(session: Session):
    item = Intelligence(
        category="macro_gold",
        status="COMPLETED",
        summary={"zh": "测试摘要", "en": "Test Summary"},
        sentiment={"zh": "看多", "en": "Bullish"},
        content="测试内容文本",
        timestamp=datetime.now(UTC),
        urgency_score=8,
        sentiment_score=0.5,
        author="Test Author",
        corroboration_count=3,
        gold_price_snapshot=2150.0
    )
    session.add(item)
    session.commit()
    
    response = client.get("/api/v1/mobile/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["summary"] == "测试摘要"
    assert data[0]["sentiment_label"] == "看多"

def test_get_mobile_dashboard_summary(session: Session):
    response = client.get("/api/v1/mobile/dashboard/summary")
    assert response.status_code == 200
    assert "market_status" in response.json()

def test_get_mobile_market_snapshot(session: Session):
    response = client.get("/api/v1/mobile/market/snapshot")
    assert response.status_code == 200
    assert response.json()["gold"]["price"] == 2150.5

def test_get_market_pulse_complex(session: Session):
    # Add multiple data points for trend aggregation
    for i in range(5):
        item = Intelligence(
            category="macro_gold",
            status="COMPLETED",
            summary={"zh": f"Point {i}"},
            timestamp=datetime.now(UTC) - timedelta(hours=i),
            urgency_score=7 + (i % 3),
            sentiment_score=0.1 * i
        )
        session.add(item)
    session.commit()
    
    response = client.get("/api/v1/mobile/market/pulse")
    assert response.status_code == 200
    data = response.json()
    assert "sentiment_trend" in data
    assert len(data["sentiment_trend"]) >= 24
    assert data["overall_sentiment"] in ["bullish", "neutral", "bearish"]
    assert "top_alerts" in data
    assert all(isinstance(alert["summary"], str) for alert in data["top_alerts"])

def test_get_mobile_intelligence_ai_summary(session: Session):
    item = Intelligence(
        summary={"zh": "Test"},
        actionable_advice={"zh": "建议买入"},
        timestamp=datetime.now(UTC)
    )
    session.add(item)
    session.commit()
    item_id = item.id
    
    response = client.get(f"/api/v1/mobile/intelligence/{item_id}/ai_summary")
    assert response.status_code == 200
    assert response.json()["ai_summary"] == "建议买入"

def test_get_mobile_intelligence_different_language(session: Session):
    item = Intelligence(
        category="macro_gold",
        status="COMPLETED",
        summary={"en": "Only English Summary"},
        timestamp=datetime.now(UTC),
        urgency_score=5
    )
    session.add(item)
    session.commit()
    
    response = client.get("/api/v1/mobile/intelligence")
    assert response.status_code == 200
    data = response.json()
    assert data[0]["summary"] == "Only English Summary"
