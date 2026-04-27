
import asyncio
from datetime import datetime, timedelta
from src.lucidpanda.core.fund_engine import FundEngine
from src.lucidpanda.core.logger import logger

# Assuming taskiq is used in the project
# from src.lucidpanda.infra.tasks.worker import broker

async def daily_fund_maintenance():
    """
    Daily maintenance task scheduled for 02:00 AM.
    """
    engine = FundEngine()
    
    logger.info("🌙 Starting Daily Fund Maintenance...")
    
    # 1. Reconcile yesterday's official NAVs (Calculates Bias for calibration)
    # We look back 2 days to ensure we catch late disclosures
    yesterday = (datetime.now() - timedelta(days=1)).date()
    logger.info(f"⚖️ Reconciling official NAVs for {yesterday}")
    engine.reconcile_official_valuations(target_date=yesterday)
    
    # 2. Run RBSA Analysis for all active funds
    # This ensures the style weights are up-to-date for today's market opening
    watchlist_codes = engine.db.get_watchlist_all_codes()
    logger.info(f"🧪 Updating RBSA weights for {len(watchlist_codes)} funds")
    
    for code in watchlist_codes:
        try:
            # Run RBSA (Phase 2)
            engine.perform_rbsa_analysis(code)
            # Give the DB/API a tiny breather
            await asyncio.sleep(0.5)
        except Exception as e:
            logger.error(f"Failed RBSA for {code}: {e}")

    # 3. Refresh Stale Holdings (Phase 1: Full Portfolio)
    logger.info("🔍 Checking for stale holdings/quarterly reports...")
    for code in watchlist_codes:
        # engine.update_fund_holdings will handle merging mid-year/annual reports
        # The engine already has internal stale-check logic
        engine.update_fund_holdings(code)
        await asyncio.sleep(0.5)

    logger.info("✅ Daily maintenance complete.")

if __name__ == "__main__":
    # For manual testing
    asyncio.run(daily_fund_maintenance())
