import os
from typing import Any

import redis
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.fund.holdings import update_fund_holdings
from src.lucidpanda.core.fund.valuation import (
    calculate_batch_valuation,
    calculate_realtime_valuation,
)
from src.lucidpanda.core.fund.reconciler import (
    reconcile_official_valuations,
    take_all_funds_snapshot,
)
from src.lucidpanda.core.logger import logger


class FundEngine:
    """
    Facade for the Fund Domain logic.
    Provides backward compatibility for existing services while delegating
    to specialized modular implementations.
    """

    def __init__(self, db: IntelligenceDB | None = None):
        self.db = db if db else IntelligenceDB()

        # Init Redis
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis = None

    def update_fund_holdings(self, fund_code: str) -> list[dict[str, Any]]:
        return update_fund_holdings(self.db, fund_code)

    def calculate_realtime_valuation(self, fund_code: str) -> dict[str, Any]:
        return calculate_realtime_valuation(self.db, self.redis, fund_code)

    def calculate_batch_valuation(self, fund_codes: list[str], summary: bool = False) -> list[dict[str, Any]]:
        return calculate_batch_valuation(self.db, self.redis, fund_codes, summary)

    def take_all_funds_snapshot(self) -> int:
        return take_all_funds_snapshot(self.db, self.redis)

    def reconcile_official_valuations(self, target_date: Any = None, fund_codes: list[str] | None = None) -> int:
        return reconcile_official_valuations(self.db, target_date, fund_codes)
