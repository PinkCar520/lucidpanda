import akshare as ak
import pandas as pd
import yfinance as yf
from datetime import datetime
from src.alphasignal.core.logger import logger
from src.alphasignal.utils import format_iso8601


class MarketTerminalService:
    """
    市场终端数据服务 - 支持四大品种
    黄金、美元指数、原油、美债 10 年期
    """

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 60  # 1 分钟缓存

    def get_market_snapshot(self):
        """
        获取市场快照（四大品种实时报价）
        """
        now = datetime.now().timestamp()
        
        # 检查缓存
        if "market_snapshot" in self._cache:
            entry = self._cache["market_snapshot"]
            if now - entry["timestamp"] < self._cache_ttl:
                return entry["data"]

        try:
            # 并行获取四个品种数据
            gold_data = self._fetch_gold()
            dxy_data = self._fetch_dxy()
            oil_data = self._fetch_oil()
            us10y_data = self._fetch_us10y()

            if not all([gold_data, dxy_data, oil_data, us10y_data]):
                logger.warning("Some market data fetch failed")

            data = {
                "gold": gold_data or self._empty_quote("GC=F", "黄金"),
                "dxy": dxy_data or self._empty_quote("DXY", "美元指数"),
                "oil": oil_data or self._empty_quote("CL=F", "原油"),
                "us10y": us10y_data or self._empty_quote("US10Y", "美债 10Y"),
                "last_updated": format_iso8601(datetime.now())
            }

            self._cache["market_snapshot"] = {"data": data, "timestamp": now}
            return data

        except Exception as e:
            logger.error(f"Failed to fetch market snapshot: {e}")
            return None

    def _fetch_gold(self):
        """获取黄金数据（COMEX + 国内现货）"""
        try:
            # COMEX 黄金期货
            df = ak.futures_global_hist_em(symbol="GC00Y")
            if not df.empty:
                latest = df.iloc[-1]
                current_price = float(latest['最新价'])
                open_price = float(latest['开盘价']) if '开盘价' in latest else float(latest['今开'])
                
                # 计算涨跌
                previous_close = float(latest['昨结']) if '昨结' in latest else open_price
                change = current_price - previous_close
                change_pct = (change / previous_close) * 100 if previous_close else 0

                return {
                    "symbol": "GC=F",
                    "name": "黄金",
                    "price": current_price,
                    "change": change,
                    "changePercent": change_pct,
                    "high_24h": float(latest['最高价']) if '最高价' in latest else None,
                    "low_24h": float(latest['最低价']) if '最低价' in latest else None,
                    "open": open_price,
                    "previous_close": previous_close,
                    "timestamp": datetime.now()
                }
        except Exception as e:
            logger.error(f"Failed to fetch gold data: {e}")
        return None

    def _fetch_dxy(self):
        """获取美元指数数据"""
        try:
            # 使用 yfinance 获取美元指数
            ticker = yf.Ticker("DX-Y.NYB")
            data = ticker.history(period="1d", interval="1m")
            
            if not data.empty:
                latest = data.iloc[-1]
                previous = data.iloc[-2] if len(data) > 1 else latest
                
                change = latest['Close'] - previous['Close']
                change_pct = (change / previous['Close']) * 100 if previous['Close'] else 0

                return {
                    "symbol": "DXY",
                    "name": "美元指数",
                    "price": float(latest['Close']),
                    "change": float(change),
                    "changePercent": float(change_pct),
                    "high_24h": float(data['High'].max()),
                    "low_24h": float(data['Low'].min()),
                    "open": float(latest['Open']),
                    "previous_close": float(previous['Close']),
                    "timestamp": datetime.now()
                }
        except Exception as e:
            logger.error(f"Failed to fetch DXY data: {e}")
        return None

    def _fetch_oil(self):
        """获取原油数据（WTI）"""
        try:
            # WTI 原油期货
            df = ak.futures_global_hist_em(symbol="CL00Y")
            if not df.empty:
                latest = df.iloc[-1]
                current_price = float(latest['最新价'])
                open_price = float(latest['开盘价']) if '开盘价' in latest else float(latest['今开'])
                
                previous_close = float(latest['昨结']) if '昨结' in latest else open_price
                change = current_price - previous_close
                change_pct = (change / previous_close) * 100 if previous_close else 0

                return {
                    "symbol": "CL=F",
                    "name": "原油",
                    "price": current_price,
                    "change": change,
                    "changePercent": change_pct,
                    "high_24h": float(latest['最高价']) if '最高价' in latest else None,
                    "low_24h": float(latest['最低价']) if '最低价' in latest else None,
                    "open": open_price,
                    "previous_close": previous_close,
                    "timestamp": datetime.now()
                }
        except Exception as e:
            logger.error(f"Failed to fetch oil data: {e}")
        return None

    def _fetch_us10y(self):
        """获取美债 10 年期收益率数据"""
        try:
            # 使用 yfinance 获取美债 10Y
            ticker = yf.Ticker("TNX")
            data = ticker.history(period="1d", interval="1m")
            
            if not data.empty:
                latest = data.iloc[-1]
                previous = data.iloc[-2] if len(data) > 1 else latest
                
                change = latest['Close'] - previous['Close']
                change_pct = (change / previous['Close']) * 100 if previous['Close'] else 0

                return {
                    "symbol": "US10Y",
                    "name": "美债 10Y",
                    "price": float(latest['Close']),
                    "change": float(change),
                    "changePercent": float(change_pct),
                    "high_24h": float(data['High'].max()),
                    "low_24h": float(data['Low'].min()),
                    "open": float(latest['Open']),
                    "previous_close": float(previous['Close']),
                    "timestamp": datetime.now()
                }
        except Exception as e:
            logger.error(f"Failed to fetch US10Y data: {e}")
        return None

    def _empty_quote(self, symbol: str, name: str):
        """返回空报价（用于降级）"""
        return {
            "symbol": symbol,
            "name": name,
            "price": 0.0,
            "change": 0.0,
            "changePercent": 0.0,
            "high_24h": None,
            "low_24h": None,
            "open": None,
            "previous_close": None,
            "timestamp": None
        }


# 单例
market_terminal_service = MarketTerminalService()
