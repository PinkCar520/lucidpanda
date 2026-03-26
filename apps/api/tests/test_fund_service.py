import unittest.mock
from unittest.mock import MagicMock, patch
import pytest
from sqlmodel import Session
from src.lucidpanda.services.fund_service import FundService

@pytest.fixture
def mock_db():
    return MagicMock(spec=Session)

@pytest.fixture
def fund_service(mock_db):
    with patch("src.lucidpanda.services.fund_service.IntelligenceDB"), \
         patch("src.lucidpanda.services.fund_service.FundEngine"):
        return FundService(mock_db)

def test_get_batch_valuation(fund_service):
    # Setup mocks
    fund_service.engine.calculate_batch_valuation.return_value = [
        {"fund_code": "000001", "valuation": 1.23}
    ]
    fund_service.db_legacy.get_fund_stats.return_value = {
        "000001": {"ytd": 0.05}
    }
    
    results = fund_service.get_batch_valuation(["000001"])
    assert len(results) == 1
    assert results[0]["fund_code"] == "000001"
    assert results[0]["stats"]["ytd"] == 0.05

def test_get_fund_valuation(fund_service):
    fund_service.engine.calculate_batch_valuation.return_value = [
        {"fund_code": "000001", "valuation": 1.23}
    ]
    fund_service.db_legacy.get_fund_stats.return_value = {}
    
    result = fund_service.get_fund_valuation("000001")
    assert result["fund_code"] == "000001"

def test_get_valuation_history(fund_service):
    from datetime import date
    fund_service.db_legacy.get_valuation_history.return_value = [
        {"trade_date": date(2023, 1, 1), "valuation": 1.0}
    ]
    
    history = fund_service.get_valuation_history("000001")
    assert len(history) == 1
    assert history[0]["trade_date"] == "2023-01-01"

def test_trigger_reconciliation(fund_service):
    fund_service.db_legacy.trigger_reconciliation.return_value = "success-info"
    
    result = fund_service.trigger_reconciliation("000001")
    assert result["success"] is True
    assert result["result"] == "success-info"
