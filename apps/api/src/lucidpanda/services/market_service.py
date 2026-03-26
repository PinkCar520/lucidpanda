import re
from datetime import datetime
from typing import Any

import akshare as ak
import requests
from src.lucidpanda.core.logger import logger
from src.lucidpanda.utils import format_iso8601


class MarketService:
    """
    Production-grade Market Data Service.
    Handles international/domestic gold price parity and exchange rates.
    """

    def __init__(self) -> None:
        # In-memory cache for indicators to prevent rate limiting
        self._cache: dict[str, Any] = {}
        self._cache_ttl: int = 60  # 1 minute

    def get_market_quotes(self, symbol: str = "GC=F") -> list[dict[str, Any]]:
        """Fetch and format market quotes for charting."""
        try:
            if symbol == "GC=F":
                df = ak.futures_global_hist_em(symbol="GC00Y")
            else:
                # Basic A-share extraction
                clean_symbol = symbol.replace("sh", "").replace("sz", "")
                df = ak.stock_zh_a_hist(symbol=clean_symbol, period="daily", adjust="qfq")

            if df.empty:
                return []

            quotes = []
            # Take last 100 days for standard chart
            for _, row in df.tail(100).iterrows():
                date_str = str(row.get('日期') or row.get('date'))
                quotes.append({
                    "date": date_str,
                    "open": float(row.get('开盘') or 0),
                    "high": float(row.get('最高') or 0),
                    "low": float(row.get('最低') or 0),
                    "close": float(row.get('收盘') or row.get('最新价') or 0),
                    "volume": float(row.get('成交量') or row.get('总量') or 0)
                })
            return quotes
        except Exception as e:
            logger.error(f"Failed to fetch market quotes for {symbol}: {e}")
            return []

    def get_gold_indicators(self) -> dict[str, Any] | None:
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

            if domestic_spot is None or fx_rate is None or intl_price_usd is None:
                return None

            # Calculation: 1 troy ounce = 31.1034768 grams
            intl_price_cny_per_gram = (intl_price_usd * fx_rate) / 31.1034768
            spread = domestic_spot - intl_price_cny_per_gram
            spread_pct = (spread / intl_price_cny_per_gram) * 100

            # At this point, type checkers should know they are not None due to the guard above
            # but we use float() for extra safety and to satisfy strict linting.
            data = {
                "domestic_spot": float(round(float(domestic_spot), 2)),
                "intl_spot_cny": float(round(float(intl_price_cny_per_gram), 2)),
                "spread": float(round(float(spread), 2)),
                "spread_pct": float(round(float(spread_pct), 2)),
                "fx_rate": float(round(float(fx_rate), 4)),
                "last_updated": format_iso8601(datetime.now()),
            }

            self._cache["gold_indicators"] = {"data": data, "timestamp": now}
            return data

        except Exception as e:
            logger.error(f"Failed to calculate gold indicators: {e}")
            return None

    def _fetch_domestic_spot(self) -> float | None:
        """Fetch AU9999 from Sina."""
        try:
            url = "https://hq.sinajs.cn/list=gds_AU9999"
            headers = {"Referer": "https://finance.sina.com.cn"}
            res = requests.get(url, headers=headers, timeout=5)
            match = re.search(r'"(.*)"', res.text)
            if match:
                parts = match.group(1).split(",")
                return float(parts[1])
        except Exception:
            pass
        return None

    def _fetch_fx_rate(self) -> float:
        """Fetch USD/CNH from Sina."""
        try:
            url = "https://hq.sinajs.cn/list=fx_susdcnh"
            headers = {"Referer": "https://finance.sina.com.cn"}
            res = requests.get(url, headers=headers, timeout=5)
            match = re.search(r'"(.*)"', res.text)
            if match:
                parts = match.group(1).split(",")
                return float(parts[1])  # parts[1] is the current price
        except Exception:
            pass
        return 7.2  # Safety fallback

    def _fetch_intl_gold_price(self) -> float | None:
        """Fetch COMEX Gold price via AkShare."""
        try:
            # Get latest quote
            df = ak.futures_global_hist_em(symbol="GC00Y")
            if not df.empty:
                return float(df.iloc[-1]["最新价"])
        except Exception:
            pass
        return None


market_service = MarketService()
