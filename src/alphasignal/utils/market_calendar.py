import pandas_market_calendars as mcal
from datetime import datetime, date, timedelta
import threading
from src.alphasignal.core.logger import logger

class MarketCalendar:
    _instance = None
    _lock = threading.Lock()
    _calendars = {}

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(MarketCalendar, cls).__new__(cls)
            return cls._instance

    def _get_calendar(self, market_code):
        """Lazy load and cache calendars (SSE, NYSE, HKEX)."""
        if market_code not in self._calendars:
            try:
                # SSE: Shanghai Stock Exchange
                # NYSE: New York Stock Exchange
                # HKEX: Hong Kong Stock Exchange
                self._calendars[market_code] = mcal.get_calendar(market_code)
            except Exception as e:
                logger.error(f"Failed to load calendar for {market_code}: {e}")
                return None
        return self._calendars[market_code]

    def is_trading_day(self, region='CN', target_date=None):
        """
        Mature check if a given date is a valid trading day for a region.
        CN: A-shares (SSE)
        US: US-stocks (NYSE)
        HK: HK-stocks (HKEX)
        """
        if target_date is None:
            target_date = date.today()
        elif isinstance(target_date, datetime):
            target_date = target_date.date()
        
        # Mapping region to Exchange code
        region_map = {
            'CN': 'SSE',
            'US': 'NYSE',
            'HK': 'HKEX'
        }
        market_code = region_map.get(region, 'SSE')
        
        cal = self._get_calendar(market_code)
        if cal is None:
            # Fallback to weekday check if calendar failed to load
            return target_date.weekday() < 5

        # Check if target_date is in the list of valid market days
        # We check a small range around the date for efficiency
        schedule = cal.schedule(start_date=target_date, end_date=target_date)
        return not schedule.empty

# Global helpers
def is_market_open(region='CN', target_date=None):
    return MarketCalendar().is_trading_day(region, target_date)

def was_market_open_last_night(region='US', target_date=None):
    """Specific for QDII: check if US/HK was open on the previous trading session relative to target_date."""
    if target_date is None:
        target_date = date.today()
    
    # Yesterday relative to our 15:00 check
    yesterday = target_date - timedelta(days=1)
    return is_market_open(region, yesterday)
