# ruff: noqa
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, text
from datetime import date, datetime
import unittest.mock as mock
import pandas as pd
import sys

# Mock database_poller before anything else
mock.patch("scripts.core.sse_server.database_poller", return_value=None).start()

# Mock external modules in sys.modules to handle local imports in calendar.py
mock_yf = mock.MagicMock()
mock_ak = mock.MagicMock()
sys.modules["yfinance"] = mock_yf
sys.modules["akshare"] = mock_ak

# Setup yfinance mock
mock_ticker_obj = mock.MagicMock()
mock_ticker_obj.calendar = pd.DataFrame(
    [datetime(2026, 3, 27)],
    index=["Earnings Date"],
    columns=["Value"]
)
mock_yf.Ticker.return_value = mock_ticker_obj

# Setup akshare mocks
mock_df = pd.DataFrame([
    {"日期": "2026-03-27", "时间": "10:00", "事件": "China PMI", "重要性": "高", "前值": "50.1", "预测值": "50.5", "公布值": "50.8"}
])
mock_ak.macro_china_pmi_yearly.return_value = mock_df
mock_ak.macro_china_cpi_yearly.return_value = mock_df
mock_ak.stock_zh_a_ex_right_date_sina.return_value = pd.DataFrame([{"除权除息日": "2026-03-27"}])
mock_ak.stock_zh_a_new_financial_analysis_sina.return_value = pd.DataFrame([{"申购日期": "2026-03-27", "股票名称": "NewStock", "股票代码": "000002"}])

from scripts.core.sse_server import app
from src.lucidpanda.models.macro_event import MacroEvent

client = TestClient(app)

@pytest.fixture(name="session")
def session_fixture(db_session):
    return db_session

def test_get_calendar_events_structure(session: Session):
    response = client.get("/api/v1/calendar/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "date_range" in data

def test_get_calendar_events_with_macro(session: Session):
    event = MacroEvent(
        event_code="CHINA_PMI",
        release_date=date(2026, 3, 27),
        release_time="10:00",
        country="CN",
        title="China PMI",
        impact_level="high",
        actual_value="50.8",
        forecast_value="50.5",
        previous_value="50.1",
        source="Test Source"
    )
    session.add(event)
    session.commit()
    
    response = client.get("/api/v1/calendar/events?start_date=2026-03-01&end_date=2026-03-31")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) >= 1
    assert any(e["title"] == "China PMI" for e in data["events"])

def test_get_calendar_events_combined_sources(session: Session):
    # Trigger symbol-based fetch
    uid = "408ba5ca-598d-4ee8-a5be-4352ab5f7918"
    session.execute(text(f"INSERT INTO fund_watchlist (fund_code, user_id, fund_name, is_deleted) VALUES ('AAPL', '{uid}', 'Apple', FALSE)"))
    session.execute(text(f"INSERT INTO fund_watchlist (fund_code, user_id, fund_name, is_deleted) VALUES ('000001', '{uid}', 'PingAn', FALSE)"))
    session.commit()
    
    response = client.get("/api/v1/calendar/events?start_date=2026-03-01&end_date=2026-03-31")
    assert response.status_code == 200
    data = response.json()
    assert len(data["events"]) > 0
