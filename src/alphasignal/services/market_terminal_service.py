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
            # 新浪财经 COMEX 黄金期货
            url = "https://hq.sinajs.cn/rn=1635506500000&list=NF_GC"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                text = resp.text
                # 解析：var hq_str_NF_GC="COMEX黄金，2837.50,2837.50,2851.30,..."
                if '="' in text:
                    parts = text.split('="')
                    if len(parts) > 1:
                        data = parts[1].strip('";').split(',')
                        if len(data) >= 12:
                            name = data[0]
                            current = float(data[1])  # 当前价
                            open_p = float(data[2]) if data[2] else current
                            high = float(data[3]) if data[3] else None
                            low = float(data[4]) if data[4] else None
                            prev_close = float(data[11]) if data[11] else current
                            change = current - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close else 0

                            return {
                                "symbol": "GC=F",
                                "name": "黄金",
                                "price": current,
                                "change": change,
                                "changePercent": change_pct,
                                "high_24h": high,
                                "low_24h": low,
                                "open": open_p,
                                "previous_close": prev_close,
                                "timestamp": datetime.now()
                            }
        except Exception as e:
            logger.error(f"Failed to fetch gold data: {e}")
        return None

    def _fetch_dxy(self):
        """获取美元指数数据（新浪财经外汇）"""
        try:
            # 新浪财经美元指数
            url = "https://hq.sinajs.cn/rn=1635506500000&list=s_DXY"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                text = resp.text
                if '="' in text:
                    parts = text.split('="')
                    if len(parts) > 1:
                        data = parts[1].strip('";').split(',')
                        if len(data) >= 12:
                            current = float(data[1]) if data[1] else 0
                            open_p = float(data[2]) if data[2] else current
                            high = float(data[3]) if data[3] else None
                            low = float(data[4]) if data[4] else None
                            prev_close = float(data[11]) if data[11] else current
                            change = current - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close else 0

                            return {
                                "symbol": "DXY",
                                "name": "美元指数",
                                "price": current,
                                "change": change,
                                "changePercent": change_pct,
                                "high_24h": high,
                                "low_24h": low,
                                "open": open_p,
                                "previous_close": prev_close,
                                "timestamp": datetime.now()
                            }
        except Exception as e:
            logger.error(f"Failed to fetch DXY data: {e}")
        return None

    def _fetch_oil(self):
        """获取原油数据（WTI 原油 - 新浪财经）"""
        try:
            # 新浪财经 WTI 原油期货
            url = "https://hq.sinajs.cn/rn=1635506500000&list=NF_CL"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                text = resp.text
                if '="' in text:
                    parts = text.split('="')
                    if len(parts) > 1:
                        data = parts[1].strip('";').split(',')
                        if len(data) >= 12:
                            current = float(data[1]) if data[1] else 0
                            open_p = float(data[2]) if data[2] else current
                            high = float(data[3]) if data[3] else None
                            low = float(data[4]) if data[4] else None
                            prev_close = float(data[11]) if data[11] else current
                            change = current - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close else 0

                            return {
                                "symbol": "CL=F",
                                "name": "原油",
                                "price": current,
                                "change": change,
                                "changePercent": change_pct,
                                "high_24h": high,
                                "low_24h": low,
                                "open": open_p,
                                "previous_close": prev_close,
                                "timestamp": datetime.now()
                            }
        except Exception as e:
            logger.error(f"Failed to fetch oil data: {e}")
        return None

    def _fetch_us10y(self):
        """获取美债 10 年期收益率数据（新浪财经）"""
        try:
            # 新浪财经美国 10 年期国债收益率
            url = "https://hq.sinajs.cn/rn=1635506500000&list=US10Y"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                text = resp.text
                if '="' in text:
                    parts = text.split('="')
                    if len(parts) > 1:
                        data = parts[1].strip('";').split(',')
                        if len(data) >= 12:
                            current = float(data[1]) if data[1] else 0
                            prev_close = float(data[11]) if data[11] else current
                            change = current - prev_close
                            change_pct = (change / prev_close) * 100 if prev_close else 0

                            return {
                                "symbol": "US10Y",
                                "name": "美债 10Y",
                                "price": current,
                                "change": change,
                                "changePercent": change_pct,
                                "high_24h": None,
                                "low_24h": None,
                                "open": current,
                                "previous_close": prev_close,
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
