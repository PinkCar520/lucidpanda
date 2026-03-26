import unittest.mock
from unittest.mock import MagicMock, patch
import pytest
import pandas as pd
from src.lucidpanda.services.market_service import MarketService

@pytest.fixture
def market_service():
    return MarketService()

def test_get_market_quotes_gold(market_service):
    # Mock akshare futures_global_hist_em
    mock_df = pd.DataFrame({
        "日期": ["2023-01-01", "2023-01-02"],
        "开盘": [1800, 1810],
        "最高": [1820, 1830],
        "最低": [1790, 1800],
        "最新价": [1810, 1820],
        "总量": [1000, 1100]
    })
    
    with patch("akshare.futures_global_hist_em", return_value=mock_df):
        quotes = market_service.get_market_quotes("GC=F")
        assert len(quotes) == 2
        assert quotes[0]["close"] == 1810
        assert quotes[1]["date"] == "2023-01-02"

def test_get_market_quotes_stock(market_service):
    # Mock akshare stock_zh_a_hist
    mock_df = pd.DataFrame({
        "日期": ["2023-01-01"],
        "开盘": [50],
        "最高": [55],
        "最低": [48],
        "收盘": [52],
        "成交量": [5000]
    })
    
    with patch("akshare.stock_zh_a_hist", return_value=mock_df):
        quotes = market_service.get_market_quotes("sh600519")
        assert len(quotes) == 1
        assert quotes[0]["close"] == 52

def test_get_gold_indicators_success(market_service):
    # Mock internal fetchers
    with patch.object(market_service, "_fetch_domestic_spot", return_value=450.0), \
         patch.object(market_service, "_fetch_fx_rate", return_value=7.2), \
         patch.object(market_service, "_fetch_intl_gold_price", return_value=1950.0):
        
        indicators = market_service.get_gold_indicators()
        assert indicators is not None
        assert indicators["domestic_spot"] == 450.0
        assert indicators["fx_rate"] == 7.2
        # intl_price_cny_per_gram = (1950 * 7.2) / 31.1034768 = ~451.39
        # spread = 450 - 451.39 = -1.39
        assert indicators["spread"] < 0 

def test_fetch_domestic_spot(market_service):
    mock_response = MagicMock()
    mock_response.text = 'var hq_str_gds_AU9999="AU9999,450.5,..." ;'
    
    with patch("requests.get", return_value=mock_response):
        price = market_service._fetch_domestic_spot()
        assert price == 450.5

def test_fetch_fx_rate(market_service):
    mock_response = MagicMock()
    mock_response.text = 'var hq_str_fx_susdcnh="USDCNH,7.215,..." ;'
    
    with patch("requests.get", return_value=mock_response):
        rate = market_service._fetch_fx_rate()
        assert rate == 7.215
