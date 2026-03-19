import schedule
import time
import sys
import os
from datetime import datetime

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.fund_engine import FundEngine
from scripts.backfills.sync_stock_industries import IndustrySyncer
from scripts.daily_tasks.calc_fund_stats import StatsEngine
from scripts.backfills.sync_fund_metadata import sync_all_funds

def run_snapshot():
    logger.info("⏰ [SCHEDULE] Triggering 15:00 Valuation Snapshot...")
    try:
        engine = FundEngine()
        engine.take_all_funds_snapshot()
    except Exception as e:
        logger.error(f"Snapshot task failed: {e}")

def run_reconciliation():
    logger.info("⏰ [SCHEDULE] Triggering Official NAV Reconciliation...")
    try:
        engine = FundEngine()
        # By default reconciles today's data
        engine.reconcile_official_valuations()
    except Exception as e:
        logger.error(f"Reconciliation task failed: {e}")

def run_daily_sync():
    logger.info("⏰ [SCHEDULE] Triggering Daily Industry & Stock Metadata Sync...")
    try:
        # Sync stocks
        syncer = IndustrySyncer()
        syncer.run()
        
        # Sync funds
        logger.info("⏰ [SCHEDULE] Triggering Daily Fund Metadata Sync...")
        sync_all_funds()
    except Exception as e:
        logger.error(f"Daily sync task failed: {e}")

def run_macro_sync():
    from scripts.daily_tasks.sync_macro_calendar import sync_macro_calendar
    logger.info("⏰ [SCHEDULE] Triggering Global Macroeconomic Calendar Sync...")
    try:
        sync_macro_calendar(days_ahead=14)
    except Exception as e:
        logger.error(f"Macro sync task failed: {e}")

def run_holiday_sync():
    from scripts.daily_tasks.sync_market_holidays import sync_market_holidays
    logger.info("⏰ [SCHEDULE] Triggering Market Holiday Sync...")
    try:
        sync_market_holidays()
    except Exception as e:
        logger.error(f"Holiday sync task failed: {e}")

def run_stats_calc():
    logger.info("⏰ [SCHEDULE] Triggering Fund Performance Stats Calculation...")
    try:
        engine = StatsEngine()
        engine.run()
    except Exception as e:
        logger.error(f"Stats calculation task failed: {e}")

def main():
    logger.info("==========================================")
    logger.info("   AlphaFunds Automation Engine Started")
    logger.info("==========================================")
    logger.info("1. 15:05 - Closing Valuation Snapshot")
    logger.info("2. 22:30 - Official NAV Reconciliation")
    logger.info("3. 01:00 - Industry & Metadata Sync")
    logger.info("4. 01:30 - Performance Stats & Grading")
    logger.info("==========================================")

    # Define Schedule
    # Snapshot at 15:05 (A-share closed, give a few mins for final prices to settle)
    schedule.every().day.at("15:05").do(run_snapshot)
    
    # Reconciliation at 22:30 (Most funds published NAV by this time)
    schedule.every().day.at("22:30").do(run_reconciliation)
    
    # Full Sync at 01:00
    schedule.every().day.at("01:00").do(run_daily_sync)

    # Stats calculation at 01:30
    schedule.every().day.at("01:30").do(run_stats_calc)
    
    # Macroeconomic Calendar Sync at 02:00
    schedule.every().day.at("02:00").do(run_macro_sync)
    
    # Market Holiday Sync at 02:05
    schedule.every().day.at("02:05").do(run_holiday_sync)

    # Log next runs
    for job in schedule.get_jobs():
        logger.info(f"📍 Next scheduled: {job.next_run} (Task: {job.job_func.__name__})")

    try:
        last_heartbeat = 0
        while True:
            schedule.run_pending()
            
            # Every 1 hour, print a heartbeat and next runs
            if time.time() - last_heartbeat > 3600:
                logger.info(f"💓 Heartbeat: System Time is {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                for job in schedule.get_jobs():
                    logger.info(f"   -> Upcoming: {job.next_run} ({job.job_func.__name__})")
                last_heartbeat = time.time()

            time.sleep(10) # Check every 10 seconds
    except KeyboardInterrupt:
        logger.info("AlphaFunds Automation Engine stopped.")

if __name__ == "__main__":
    main()
