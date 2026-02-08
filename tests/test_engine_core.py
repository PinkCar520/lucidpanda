import pytest
from unittest.mock import MagicMock, patch
from src.alphasignal.core.engine import AlphaEngine

# Mock dependencies used in AlphaEngine.__init__
@pytest.fixture
def mock_dependencies(mocker):
    # Mock Config
    mocker.patch('src.alphasignal.core.engine.settings', autospec=True)
    
    # Mock Data Sources
    mock_google = mocker.patch('src.alphasignal.core.engine.GoogleNewsSource')
    mock_rss = mocker.patch('src.alphasignal.core.engine.RSSHubSource')
    
    # Mock LLMs
    mock_gemini = mocker.patch('src.alphasignal.core.engine.GeminiLLM')
    mock_deepseek = mocker.patch('src.alphasignal.core.engine.DeepSeekLLM')
    
    # Mock Database
    mock_db = mocker.patch('src.alphasignal.core.engine.IntelligenceDB')
    mock_db.return_value.get_latest_indicator.return_value = {
        'timestamp': '2026-02-08',
        'indicator_name': 'COT_GOLD_NET',
        'value': 1000,
        'percentile': 50,
        'description': 'Test'
    }
    
    # Mock Channels
    mock_email = mocker.patch('src.alphasignal.core.engine.EmailChannel')
    mock_bark = mocker.patch('src.alphasignal.core.engine.BarkChannel')
    
    # Mock Backtester
    mock_backtester = mocker.patch('src.alphasignal.core.engine.BacktestEngine')

    return {
        'google': mock_google,
        'rss': mock_rss,
        'gemini': mock_gemini,
        'deepseek': mock_deepseek,
        'db': mock_db,
        'email': mock_email,
        'bark': mock_bark,
        'backtester': mock_backtester
    }

@pytest.fixture
def engine(mock_dependencies):
    # Initialize engine with mocked classes
    return AlphaEngine()

def test_run_once_no_items(engine):
    """Test that engine does nothing if no items are found."""
    # Setup: all sources return empty list
    for source in engine.sources:
        source.fetch.return_value = []
    
    engine.run_once()
    
    # Verify: No processing happened
    engine.db.is_duplicate.assert_not_called()
    engine.primary_llm.analyze.assert_not_called()

def test_run_once_with_new_item(engine):
    """Test full flow: fetch -> analyze -> save -> dispatch."""
    # Setup: Source returns one item
    item = {'title': 'Test News', 'url': 'http://test.com', 'content': 'Test Content'}
    engine.sources[0].fetch.return_value = [item]
    # Other sources empty
    for source in engine.sources[1:]:
        source.fetch.return_value = []
        
    # Mock DB: Not duplicate
    engine.db.is_duplicate.return_value = False
    
    # Mock LLM analysis result
    analysis = {
        'summary': 'Summary',
        'sentiment': 'Bullish',
        'urgency_score': 8,
        'actionable_advice': 'Buy',
        'market_implication': {'Gold': 'Up'}
    }
    engine.primary_llm.analyze.return_value = analysis
    
    # Run
    engine.run_once()
    
    # Verify
    # 1. Fetched
    engine.sources[0].fetch.assert_called()
    
    # 2. Checked duplicate
    engine.db.is_duplicate.assert_called_with('Test News', 'http://test.com')
    
    # 3. Analyzed (with primary LLM)
    engine.primary_llm.analyze.assert_called()
    
    # 4. Saved to DB
    engine.db.save_intelligence.assert_called()
    
    # 5. Dispatched to channels
    for channel in engine.channels:
        channel.send.assert_called()

def test_process_duplicate_item(engine):
    """Test that duplicate items are skipped."""
    item = {'title': 'Test News', 'url': 'http://test.com', 'content': 'Test Content'}
    engine.sources[0].fetch.return_value = [item]
    
    # Mock DB: IS duplicate
    engine.db.is_duplicate.return_value = True
    
    engine.run_once()
    
    # Verify logic stopped after duplicate check
    engine.db.is_duplicate.assert_called()
    engine.primary_llm.analyze.assert_not_called()
    engine.db.save_intelligence.assert_not_called()

def test_llm_fallback(engine):
    """Test fallback to secondary LLM if primary fails."""
    item = {'title': 'Test News', 'url': 'http://test.com', 'content': 'Test Content'}
    engine.sources[0].fetch.return_value = [item]
    engine.db.is_duplicate.return_value = False
    
    # Setup Primary LLM failure
    engine.primary_llm.analyze.side_effect = Exception("API Error")
    
    # Setup Fallback LLM success
    analysis = {'summary': 'Fallback Summary'}
    engine.fallback_llm.analyze.return_value = analysis
    
    engine.run_once()
    
    # Verify
    engine.primary_llm.analyze.assert_called()
    engine.fallback_llm.analyze.assert_called() # Should call fallback
    engine.db.save_intelligence.assert_called() # Should still save

