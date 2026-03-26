from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_dependencies(mocker):
    mocker.patch('src.lucidpanda.core.engine.settings', autospec=True)

    mock_gemini   = mocker.patch('src.lucidpanda.core.engine.GeminiLLM')
    mock_deepseek = mocker.patch('src.lucidpanda.core.engine.DeepSeekLLM')

    mock_db = mocker.patch('src.lucidpanda.core.engine.IntelligenceDB')
    mock_db.return_value.get_latest_indicator.return_value = {
        'timestamp': '2026-02-08', 'indicator_name': 'COT_GOLD_NET',
        'value': 1000, 'percentile': 50, 'description': 'Test'
    }
    mock_db.return_value.get_pending_intelligence.return_value = []
    mock_db.return_value.compute_source_credibility.return_value = {}
    mock_db.return_value.get_recent_intelligence.return_value = []

    # Mock deduplicator: not duplicate by default
    mock_dedup = mocker.patch('src.lucidpanda.core.engine.NewsDeduplicator')
    mock_dedup.return_value.is_duplicate.return_value = False
    mock_dedup.return_value.last_vector = None

    mock_email = mocker.patch('src.lucidpanda.core.engine.EmailChannel')
    mock_bark  = mocker.patch('src.lucidpanda.core.engine.BarkChannel')
    mock_bt    = mocker.patch('src.lucidpanda.core.engine.BacktestEngine')
    mock_bt.return_value.sync_outcomes.return_value = None

    return {
        'gemini': mock_gemini, 'deepseek': mock_deepseek,
        'db': mock_db, 'email': mock_email, 'bark': mock_bark,
        'backtester': mock_bt, 'dedup': mock_dedup,
    }


@pytest.fixture
def engine(mock_dependencies):
    from src.lucidpanda.core.engine import AlphaEngine
    eng = AlphaEngine()
    eng._fetch_round_snapshot = MagicMock(return_value={
        'gold_price_snapshot': 1900.0, 'dxy_snapshot': 103.0,
        'us10y_snapshot': 4.2, 'gvz_snapshot': 15.0,
    })
    return eng


def test_engine_has_no_sources(engine):
    """AlphaEngine 不再维护 sources，RSS 采集由 RSSCollector 负责。"""
    assert not hasattr(engine, 'sources'), \
        "engine.sources should not exist — use RSSCollector instead"


def test_run_once_no_pending(engine):
    """没有 PENDING 记录时，引擎直接返回，不调用 AI。"""
    engine.db.get_pending_intelligence.return_value = []
    engine.run_once()
    engine.primary_llm.generate_json_async.assert_not_called()


def test_run_once_with_pending_item(engine):
    """有 PENDING 记录时，正常完成 AI 分析 → 存储。"""
    pending_item = {
        'id': 1, 'source_id': 'http://test.com/1',
        'content': 'Fed raises rates sharply',
        'url': 'http://test.com/1',
        'gold_price_snapshot': 1900.0, 'dxy_snapshot': 103.0,
        'us10y_snapshot': 4.2, 'gvz_snapshot': 15.0, 'fed_val': -1,
    }
    engine.db.get_pending_intelligence.return_value = [pending_item]
    engine.deduplicator.is_duplicate.return_value = False

    analysis = {
        'summary': {'zh': '美联储加息', 'en': 'Fed rate hike'},
        'sentiment': {'zh': '利空黄金', 'en': 'Bearish'},
        'urgency_score': 8, 'sentiment_score': -0.7,
        'actionable_advice': {'zh': '减仓', 'en': 'Reduce'},
        'market_implication': {'zh': '黄金下行压力', 'en': 'Gold downside'},
    }
    plan = {"use_tools": False, "plan_summary": "No tools", "tool_calls": []}
    engine.primary_llm.generate_json_async = AsyncMock(side_effect=[plan, analysis])

    engine.run_once()

    engine.primary_llm.generate_json_async.assert_called()
    engine.db.update_intelligence_analysis.assert_called()


def test_llm_fallback(engine):
    """主 LLM 失败时，使用备用 LLM。"""
    pending_item = {
        'id': 1, 'source_id': 'http://test.com/2',
        'content': 'Geopolitical tensions rise',
        'url': 'http://test.com/2',
        'gold_price_snapshot': 1950.0, 'fed_val': 0,
    }
    engine.db.get_pending_intelligence.return_value = [pending_item]
    engine.deduplicator.is_duplicate.return_value = False

    engine.primary_llm.generate_json_async = AsyncMock(side_effect=Exception("API Error"))
    engine.primary_llm.analyze_async = AsyncMock(side_effect=Exception("API Error"))
    engine.fallback_llm.analyze_async = AsyncMock(return_value={
        'summary': {'en': 'Fallback'}, 'sentiment': {'en': 'Bullish'},
        'urgency_score': 6, 'sentiment_score': 0.5,
        'actionable_advice': {'en': 'Hold'},
        'market_implication': {'en': 'Gold up'},
    })

    engine.run_once()

    engine.primary_llm.analyze_async.assert_called()
    engine.fallback_llm.analyze_async.assert_called()
