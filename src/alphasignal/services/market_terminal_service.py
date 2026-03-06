import akshare as ak
import pandas as pd
from datetime import datetime
import requests
from src.alphasignal.core.logger import logger
from src.alphasignal.utils import format_iso8601


class MarketTerminalService:
    """
    市场终端数据服务 - 支持四大品种
    黄金、美元指数、原油、美债 10 年期
    使用新浪财经 API（更稳定）
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
        """获取黄金数据（COMEX 黄金 - 新浪财经）"""
        try:
            # 使用新浪期货 GlobalFuturesService 接口 (同 market.py)
            url = "https://stock.finance.sina.com.cn/futures/api/json_v2.php/GlobalFuturesService.getGlobalFuturesMinLine?symbol=XAU"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if data and isinstance(data, dict):
                key = list(data.keys())[0]
                points = data[key]
                if points:
                    current = float(points[-1][1])
                    return {
                        "symbol": "GC=F",
                        "name": "黄金",
                        "price": current,
                        "change": 0.0,
                        "changePercent": 0.0,
                        "high_24h": None,
                        "low_24h": None,
                        "open": current,
                        "previous_close": current,
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            logger.error(f"Failed to fetch gold data: {e}")
            
        try:
            # 备选: 东方财富
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=120.XAUUSD&ut=fa5fd1943c0a30548d390f18a2cd7645&fields1=f1&fields2=f53&klt=1&fqt=0&lmt=1"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if data and "data" in data and data["data"]["klines"]:
                val = data["data"]["klines"][0].split(",")[1]
                current = float(val)
                return {
                    "symbol": "GC=F",
                    "name": "黄金",
                    "price": current,
                    "change": 0.0,
                    "changePercent": 0.0,
                    "high_24h": None,
                    "low_24h": None,
                    "open": current,
                    "previous_close": current,
                    "timestamp": datetime.now()
                }
        except Exception as e:
            logger.error(f"Failed to fetch gold data (EastMoney): {e}")
        return None

    def _fetch_dxy(self):
        """获取美元指数数据（新浪财经外汇）"""
        try:
            # 美元指数 (DINIW)
            url = "https://hq.sinajs.cn/list=DINIW"
            resp = requests.get(url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"})
            raw = resp.text
            if "=\"" in raw and len(raw.split("\"")[1].split(",")) > 1:
                val = raw.split("\"")[1].split(",")[1]
                if val and val != '0':
                    current = float(val)
                    return {
                        "symbol": "DXY",
                        "name": "美元指数",
                        "price": current,
                        "change": 0.0,
                        "changePercent": 0.0,
                        "high_24h": None,
                        "low_24h": None,
                        "open": current,
                        "previous_close": current,
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            logger.error(f"Failed to fetch DXY data: {e}")
        return None

    def _fetch_oil(self):
        """获取原油数据（WTI 原油 - 新浪财经）"""
        try:
            # 新浪期货 GlobalFuturesService 接口
            url = "https://stock.finance.sina.com.cn/futures/api/json_v2.php/GlobalFuturesService.getGlobalFuturesMinLine?symbol=CL"
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if data and isinstance(data, dict):
                key = list(data.keys())[0]
                points = data[key]
                if points:
                    current = float(points[-1][1])
                    return {
                        "symbol": "CL=F",
                        "name": "原油",
                        "price": current,
                        "change": 0.0,
                        "changePercent": 0.0,
                        "high_24h": None,
                        "low_24h": None,
                        "open": current,
                        "previous_close": current,
                        "timestamp": datetime.now()
                    }
        except Exception as e:
            logger.error(f"Failed to fetch oil data: {e}")
        return None

    def _fetch_us10y(self):
        """获取美债 10 年期收益率数据（新浪财经）"""
        try:
            # AkShare 债券数据 (同 market.py 方案 A)
            df = ak.bond_zh_us_rate()
            if not df.empty:
                rate_col = next((c for c in df.columns if '10' in c), None)
                if rate_col:
                    val = df.iloc[-1][rate_col]
                    if val and float(val) > 0:
                        current = round(float(val), 3)
                        return {
                            "symbol": "US10Y",
                            "name": "美债 10Y",
                            "price": current,
                            "change": 0.0,
                            "changePercent": 0.0,
                            "high_24h": None,
                            "low_24h": None,
                            "open": current,
                            "previous_close": current,
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
