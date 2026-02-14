import requests
import re
import pandas as pd
import akshare as ak
from datetime import datetime
from src.alphasignal.core.logger import logger
from src.alphasignal.utils import format_iso8601

class MarketService:
    """
    Production-grade Market Data Service.
    Handles international/domestic gold price parity and exchange rates.
    """
    
    def __init__(self):
        # In-memory cache for indicators to prevent rate limiting
        self._cache = {}
        self._cache_ttl = 60 # 1 minute
    
    def get_gold_indicators(self):
        """
        Calculate Gold Spread (CNY/g) between Domestic (AU9999) and Intl (COMEX).
        Refactored from Next.js Node.js implementation.
        """
        now = datetime.now().timestamp()
        if "gold_indicators" in self._cache:
            entry = self._cache["gold_indicators"]
            if now - entry["timestamp"] < self._cache_ttl:
                return entry["data"]

        try:
            # 1. Fetch Domestic Spot (AU9999) from Sina
            domestic_spot = self._fetch_domestic_spot()
            
            # 2. Fetch FX Rate (USD/CNH) from Sina or AkShare
            fx_rate = self._fetch_fx_rate()
            
            # 3. Fetch Intl Gold (COMEX GC)
            # We use akshare for the latest quote
            intl_price_usd = self._fetch_intl_gold_price()
            
            if not all([domestic_spot, fx_rate, intl_price_usd]):
                return None

            # Calculation: 1 troy ounce = 31.1034768 grams
            intl_price_cny_per_gram = (intl_price_usd * fx_rate) / 31.1034768
            spread = domestic_spot - intl_price_cny_per_gram
            spread_pct = (spread / intl_price_cny_per_gram) * 100

            data = {
                "domestic_spot": round(domestic_spot, 2),
                "intl_spot_cny": round(intl_price_cny_per_gram, 2),
                "spread": round(spread, 2),
                "spread_pct": round(spread_pct, 2),
                "fx_rate": round(fx_rate, 4),
                "last_updated": format_iso8601(datetime.now())
            }
            
            self._cache["gold_indicators"] = {"data": data, "timestamp": now}
            return data

        except Exception as e:
            logger.error(f"Failed to calculate gold indicators: {e}")
            return None

    def _fetch_domestic_spot(self):
        """Fetch AU9999 from Sina."""
        try:
            url = "https://hq.sinajs.cn/list=gds_AU9999"
            headers = {"Referer": "https://finance.sina.com.cn"}
            res = requests.get(url, headers=headers, timeout=5)
            match = re.search(r'"(.*)"', res.text)
            if match:
                parts = match.group(1).split(',')
                return float(parts[1])
        except: pass
        return None

    def _fetch_fx_rate(self):
        """Fetch USD/CNH from Sina."""
        try:
            url = "https://hq.sinajs.cn/list=fx_susdcnh"
            headers = {"Referer": "https://finance.sina.com.cn"}
            res = requests.get(url, headers=headers, timeout=5)
            match = re.search(r'"(.*)"', res.text)
            if match:
                parts = match.group(1).split(',')
                return float(parts[1]) # parts[1] is the current price
        except: pass
        return 7.2 # Safety fallback
        
    def _fetch_intl_gold_price(self):
        """Fetch COMEX Gold price via AkShare."""
        try:
            # Get latest quote
            df = ak.futures_global_hist_em(symbol="GC00Y")
            if not df.empty:
                return float(df.iloc[-1]['最新价'])
        except: pass
        return None

market_service = MarketService()
