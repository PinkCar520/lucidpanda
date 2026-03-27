import threading
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas_market_calendars as mcal

from src.lucidpanda.core.logger import logger


class MarketCalendar:
    _instance = None
    _lock = threading.Lock()
    _calendars = {}

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
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

    def is_trading_day(self, region="CN", target_date=None):
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

        # Mapping region/type to Exchange code
        region_map = {"CN": "SSE", "US": "NYSE", "HK": "HKEX", "GOLD": "CMEGlobex_GC"}
        market_code = region_map.get(region, "SSE")

        cal = self._get_calendar(market_code)
        if cal is None:
            # Fallback to weekday check if calendar failed to load
            return target_date.weekday() < 5

        # Check if target_date is in the list of valid market days
        try:
            # CME Globex Gold is usually open 24/5.
            # We check if it's a trading day first.
            schedule = cal.schedule(start_date=target_date, end_date=target_date)
            return not schedule.empty
        except Exception:
            return target_date.weekday() < 5


# Global helpers
def is_market_open(region="CN", target_date=None):
    return MarketCalendar().is_trading_day(region, target_date)


def is_gold_market_open(target_date=None):
    """Specific for COMEX Gold (GC) market calendar."""
    return MarketCalendar().is_trading_day("GOLD", target_date)


def was_market_open_last_night(region="US", target_date=None):
    """Specific for QDII: check if US/HK was open on the previous trading session relative to target_date."""
    if target_date is None:
        target_date = date.today()

    # Yesterday relative to our 15:00 check
    yesterday = target_date - timedelta(days=1)
    return is_market_open(region, yesterday)


def get_market_status(region="CN", target_dt=None):
    """
    Return coarse intraday market status for client display.
    Values: OPEN / LUNCH_BREAK / CLOSED
    """
    if target_dt is None:
        target_dt = datetime.now(UTC)
    if isinstance(target_dt, date) and not isinstance(target_dt, datetime):
        target_dt = datetime.combine(target_dt, datetime.min.time())

    region_upper = (region or "CN").upper()
    tz_map = {
        "CN": "Asia/Shanghai",
        "US": "America/New_York",
        "HK": "Asia/Hong_Kong",
        "GOLD": "America/New_York",
    }
    tz_name = tz_map.get(region_upper, "Asia/Shanghai")
    tz = ZoneInfo(tz_name)

    if target_dt.tzinfo is None:
        local_dt = target_dt.replace(tzinfo=tz)
    else:
        local_dt = target_dt.astimezone(tz)

    target_day = local_dt.date()
    # 这里的 is_market_open (is_trading_day) 已经处理了节假日逻辑
    if not is_market_open(region_upper, target_day):
        return "CLOSED"

    minute_of_day = local_dt.hour * 60 + local_dt.minute

    if region_upper == "CN":
        # A-share: 09:30-11:30, 13:00-15:00
        if 9 * 60 + 30 <= minute_of_day < 11 * 60 + 30:
            return "OPEN"
        if 11 * 60 + 30 <= minute_of_day < 13 * 60:
            return "LUNCH_BREAK"
        if 13 * 60 <= minute_of_day < 15 * 60:
            return "OPEN"
        return "CLOSED"

    if region_upper in ["US", "HK"]:
        # US/HK: 09:30-16:00 (Coarse)
        if 9 * 60 + 30 <= minute_of_day < 16 * 60:
            return "OPEN"
        return "CLOSED"

    if region_upper == "GOLD":
        # CME Globex Gold:
        # Sunday - Friday 6:00 p.m. – 5:00 p.m. ET
        # (18:00 - 17:00 next day)
        # Daily break: 17:00 - 18:00 ET
        if 17 * 60 <= minute_of_day < 18 * 60:
            return "CLOSED"
        return "OPEN"

    return "CLOSED"
