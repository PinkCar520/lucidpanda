
import unittest
from unittest.mock import MagicMock, patch
import sys

# Mock heavy modules BEFORE importing FundEngine
mock_ak = MagicMock()
sys.modules["akshare"] = mock_ak
mock_redis_mod = MagicMock()
sys.modules["redis"] = mock_redis_mod

from datetime import date, timedelta
from src.lucidpanda.core.fund_engine import FundEngine

class TestFundConfidence(unittest.TestCase):
    def setUp(self):
        # Mock the DB and Redis to avoid actual connections
        self.mock_db = MagicMock()
        self.mock_redis = MagicMock()
        
        with patch('redis.from_url', return_value=self.mock_redis):
            self.engine = FundEngine(db=self.mock_db)

    def test_high_confidence_new_report(self):
        """Scenario: Report is 5 days old and accuracy is high."""
        fund_code = "001234"
        recent_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        
        # Mock DB responses
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.1, "sample_count": 5}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": recent_date}]
        self.mock_db.get_recent_tracking_statuses.return_value = [
            {"status": "S", "deviation": 0.05},
            {"status": "S", "deviation": -0.02},
            {"status": "S", "deviation": 0.08}
        ]

        result = self.engine._get_confidence_level(fund_code, 95.0, {})
        
        print(f"\n[High Confidence Test] Result: {result['level']} (Score: {result['score']})")
        self.assertEqual(result["level"], "high")
        self.assertIn("new_report", result["reasons"])
        self.assertGreaterEqual(result["score"], 80)

    def test_medium_confidence_stale_report(self):
        """Scenario: Report is 70 days old, but tracking is still okay."""
        fund_code = "005678"
        stale_date = (date.today() - timedelta(days=70)).strftime("%Y-%m-%d")
        
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.3, "sample_count": 5}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": stale_date}]
        self.mock_db.get_recent_tracking_statuses.return_value = [
            {"status": "A", "deviation": 0.25},
            {"status": "S", "deviation": 0.10},
            {"status": "A", "deviation": -0.22}
        ]

        result = self.engine._get_confidence_level(fund_code, 92.0, {})
        
        print(f"[Medium Confidence Test] Result: {result['level']} (Score: {result['score']})")
        self.assertEqual(result["level"], "medium")
        self.assertIn("possible_rebalance", result["reasons"])
        self.assertTrue(result["is_suspected_rebalance"])

    def test_low_confidence_significant_drift(self):
        """Scenario: 3 consecutive days of drift > 0.3%."""
        fund_code = "009999"
        report_date = (date.today() - timedelta(days=30)).strftime("%Y-%m-%d")
        
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.4, "sample_count": 5}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": report_date}]
        # Drift: all > 0.3
        self.mock_db.get_recent_tracking_statuses.return_value = [
            {"status": "B", "deviation": 0.35},
            {"status": "B", "deviation": 0.42},
            {"status": "C", "deviation": 0.55}
        ]

        result = self.engine._get_confidence_level(fund_code, 90.0, {})
        
        print(f"[Low Confidence - Drift Test] Result: {result['level']} (Score: {result['score']})")
        self.assertEqual(result["level"], "low")
        self.assertIn("significant_drift", result["reasons"])

    def test_low_confidence_poor_accuracy(self):
        """Scenario: High MAE (Mean Absolute Error)."""
        fund_code = "008888"
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.6, "sample_count": 5}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": "2023-12-31"}]
        self.mock_db.get_recent_tracking_statuses.return_value = []

        result = self.engine._get_confidence_level(fund_code, 85.0, {})
        
        print(f"[Low Confidence - Accuracy Test] Result: {result['level']} (Score: {result['score']})")
        self.assertEqual(result["level"], "low")
        self.assertIn("accuracy_poor", result["reasons"])

if __name__ == "__main__":
    unittest.main()
