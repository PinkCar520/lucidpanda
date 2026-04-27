
import unittest
from unittest import mock
from datetime import date, datetime, timedelta

# Simplified class to test ONLY the logic of _get_confidence_level
class ConfidenceEngineTester:
    def __init__(self, db_mock):
        self.db = db_mock

    def _get_confidence_level(self, fund_code, current_weight, fund_meta):
        # PASTE THE EXACT LOGIC FROM fund_engine.py HERE
        import pytz
        from datetime import date

        # 0. Fetch necessary data
        perf = self.db.get_fund_performance_metrics(fund_code, days=7)
        mae = perf.get("avg_mae")
        
        holdings = self.db.get_fund_holdings(fund_code)
        report_date_str = holdings[0].get("report_date", "") if holdings else ""
        
        recent_history = self.db.get_recent_tracking_statuses(fund_code, limit=3)
        
        # 1. Calculate Age Factor
        days_since_report = 999
        if report_date_str:
            try:
                if "Q" in report_date_str:
                    y, q = report_date_str.split("Q")
                    month_end = {"1": 3, "2": 6, "3": 9, "4": 12}[q]
                    r_date = date(int(y), month_end, 28) 
                else:
                    r_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
                
                days_since_report = (date.today() - r_date).days
            except Exception:
                pass

        is_drifting = False
        if len(recent_history) >= 3:
            is_drifting = all(abs(h["deviation"]) > 0.3 for h in recent_history)

        level = "medium"
        score = 60
        reasons = []

        if days_since_report <= 14 and (mae is None or mae < 0.2):
            level = "high"
            score = 90
            reasons.append("new_report")
            if mae is not None:
                reasons.append("accuracy_high")
        elif is_drifting or (mae is not None and mae >= 0.5):
            level = "low"
            score = 30
            if is_drifting:
                reasons.append("significant_drift")
            if mae is not None and mae >= 0.5:
                reasons.append("accuracy_poor")
            if days_since_report > 60:
                reasons.append("outdated_report")
        else:
            level = "medium"
            score = 60
            if days_since_report > 60:
                reasons.append("possible_rebalance")
            if mae is not None and mae < 0.5:
                reasons.append("accuracy_medium")

        if current_weight < 70:
            score = max(0, score - 20)
            reasons.append("coverage_low")

        return {
            "level": level,
            "score": score,
            "is_suspected_rebalance": is_drifting or (days_since_report > 60),
            "days_since_report": days_since_report,
            "reasons": reasons,
        }

class TestFundConfidence(unittest.TestCase):
    def setUp(self):
        self.mock_db = mock.MagicMock()
        self.tester = ConfidenceEngineTester(self.mock_db)

    def test_high_confidence(self):
        recent_date = (date.today() - timedelta(days=5)).strftime("%Y-%m-%d")
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.1}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": recent_date}]
        self.mock_db.get_recent_tracking_statuses.return_value = []
        
        res = self.tester._get_confidence_level("001234", 95, {})
        print(f"High Conf: {res}")
        self.assertEqual(res["level"], "high")

    def test_low_confidence_drift(self):
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.2}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": "2024-01-01"}]
        self.mock_db.get_recent_tracking_statuses.return_value = [
            {"deviation": 0.4}, {"deviation": 0.5}, {"deviation": 0.6}
        ]
        
        res = self.tester._get_confidence_level("001234", 95, {})
        print(f"Low Conf (Drift): {res}")
        self.assertEqual(res["level"], "low")
        self.assertIn("significant_drift", res["reasons"])

    def test_medium_confidence_stale(self):
        stale_date = (date.today() - timedelta(days=70)).strftime("%Y-%m-%d")
        self.mock_db.get_fund_performance_metrics.return_value = {"avg_mae": 0.2}
        self.mock_db.get_fund_holdings.return_value = [{"report_date": stale_date}]
        self.mock_db.get_recent_tracking_statuses.return_value = []
        
        res = self.tester._get_confidence_level("001234", 95, {})
        print(f"Medium Conf (Stale): {res}")
        self.assertEqual(res["level"], "medium")
        self.assertTrue(res["is_suspected_rebalance"])

if __name__ == "__main__":
    unittest.main()
