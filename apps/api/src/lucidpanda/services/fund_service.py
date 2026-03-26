import logging
from typing import Any

from sqlmodel import Session
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.fund_engine import FundEngine

logger = logging.getLogger(__name__)


class FundService:
    def __init__(self, db: Session):
        self.db = db
        self.db_legacy = IntelligenceDB()
        self.engine = FundEngine()

    def get_batch_valuation(self, codes: list[str], summary: bool = False) -> list[dict[str, Any]]:
        results = self.engine.calculate_batch_valuation(codes, summary=summary)
        stats_map = self.db_legacy.get_fund_stats(codes)

        for res in results:
            f_code = res.get('fund_code')
            if f_code in stats_map:
                res['stats'] = stats_map[f_code]
        return results

    def get_fund_valuation(self, code: str) -> dict[str, Any] | None:
        results = self.get_batch_valuation([code])
        if results:
            return results[0]
        return None

    def get_valuation_history(self, code: str, limit: int = 30) -> list[dict[str, Any]]:
        history = self.db_legacy.get_valuation_history(code, limit)
        formatted_history = []
        for h in history:
            item = dict(h)
            if 'trade_date' in item and hasattr(item['trade_date'], 'isoformat'):
                item['trade_date'] = item['trade_date'].isoformat()
            formatted_history.append(item)
        return formatted_history

    def trigger_reconciliation(self, fund_code: str | None = None) -> dict[str, Any]:
        result = self.db_legacy.trigger_reconciliation(fund_code)
        return {"success": True, "result": result}
