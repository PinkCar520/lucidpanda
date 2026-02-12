import akshare as ak
import pandas as pd
from datetime import datetime, date
import threading
from src.alphasignal.core.logger import logger

class MarketCalendar:
    _instance = None
    _lock = threading.Lock()
    _trade_dates_cache = set()
    _last_sync_year = None

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MarketCalendar, cls).__new__(cls)
            return cls._instance

    def _sync_trade_dates(self):
        """Fetch A-share trading dates from Sina via AkShare."""
        current_year = datetime.now().year
        if self._last_sync_year == current_year and self._trade_dates_cache:
            return

        try:
            logger.info("📅 Syncing market trade dates from source...")
            # Fetch a broad range to cover recent and future dates
            df = ak.tool_trade_date_hist_sina()
            if not df.empty:
                # df usually has a column 'trade_date'
                dates = pd.to_datetime(df['trade_date']).dt.date.tolist()
                self._trade_dates_cache = set(dates)
                self._last_sync_year = current_year
                logger.info(f"✅ Synced {len(dates)} trade dates.")
        except Exception as e:
            logger.error(f"❌ Failed to sync trade dates: {e}")

    def is_trading_day(self, target_date=None):
        """Check if a given date is a valid A-share trading day."""
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # 1. Quick check for weekends (obvious non-trading days)
        if target_date.weekday() >= 5: # 5 is Sat, 6 is Sun
            return False

        # 2. Check against official calendar
        self._sync_trade_dates()
        return target_date in self._trade_dates_cache

# Global helper
def is_market_open(target_date=None):
    return MarketCalendar().is_trading_day(target_date)
