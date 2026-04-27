import re
from datetime import datetime

import akshare as ak
import requests

from src.lucidpanda.core.logger import logger
from src.lucidpanda.utils import format_iso8601


class MarketTerminalService:
    """
    市场终端数据服务 - 支持多品种实时报价
    黄金（伦敦金/上海金）、美元指数、原油、美债 10 年期
    """

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 15  # 15 秒缓存

    def get_market_snapshot(self):
        """
        获取市场快照（多品种实时报价）
        """
        now = datetime.now().timestamp()

        # 检查缓存
        if "market_snapshot" in self._cache:
            entry = self._cache["market_snapshot"]
            if now - entry["timestamp"] < self._cache_ttl:
                return entry["data"]

        try:
            # 并行获取各品种数据
            gold_data = self._fetch_gold()
            gold_cny_data = self._fetch_gold_cny()
            dxy_data = self._fetch_dxy()
            oil_data = self._fetch_oil()
            us10y_data = self._fetch_us10y()

            data = {
                "gold": gold_data or self._empty_quote("XAU", "伦敦金"),
                "gold_cny": gold_cny_data or self._empty_quote("AU9999", "上海金"),
                "dxy": dxy_data or self._empty_quote("DXY", "美元指数"),
                "oil": oil_data or self._empty_quote("CL=F", "原油"),
                "us10y": us10y_data or self._empty_quote("US10Y", "美债 10Y"),
                "last_updated": format_iso8601(datetime.now()),
            }

            self._cache["market_snapshot"] = {"data": data, "timestamp": now}
            return data

        except Exception as e:
            logger.error(f"Failed to fetch market snapshot: {e}")
            return None

    def _fetch_gold_cny(self):
        """获取上海金数据 (AU9999) - 新浪财经"""
        try:
            url = "http://hq.sinajs.cn/list=s_sh000001,sz399001,gds_AU9999"
            headers = {"Referer": "http://finance.sina.com.cn"}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                # 解析格式: var hq_str_gds_AU9999="上海金,614.50,1.25,0.20,...";
                match = re.search(r'hq_str_gds_AU9999="([^"]+)"', resp.text)
                if match:
                    parts = match.group(1).split(",")
                    price = float(parts[1])
                    change = float(parts[2])
                    change_pct = float(parts[3])
                    return {
                        "symbol": "AU9999",
                        "name": "上海金",
                        "price": price,
                        "change": change,
                        "changePercent": change_pct
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to fetch gold_cny: {e}")
            return None

    def _fetch_gold(self):
        """获取黄金数据（伦敦金现货 - 对标国际基准）"""
        try:
            # 兼容性修复：尝试多种 AkShare 接口
            df = None
            try:
                df = ak.gold_zh_spot_qhkd()
            except:
                try:
                    df = ak.gold_zh_spot_sina()
                except:
                    pass
            
            if df is not None and not df.empty:
                # 在结果中过滤伦敦金
                row = df[df["名称"].str.contains("伦敦金|London Gold", case=False, na=False)]
                if not row.empty:
                    current = float(row.iloc[0]["最新价"])
                    change = float(row.iloc[0]["涨跌额"])
                    change_pct = float(row.iloc[0]["涨跌幅"])
                    
                    return {
                        "symbol": "XAU",
                        "name": "伦敦金",
                        "price": current,
                        "change": round(change, 2),
                        "changePercent": round(change_pct, 2),
                        "timestamp": format_iso8601(datetime.now()),
                    }
        except Exception as e:
            logger.error(f"Failed to fetch London Gold spot: {e}")
        return None

    def _fetch_dxy(self):
        """获取美元指数数据（新浪财经外汇 DINIW）"""
        try:
            url = "https://hq.sinajs.cn/list=DINIW"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw and len(raw.split('"')[1].split(",")) > 8:
                parts = raw.split('"')[1].split(",")
                current = float(parts[1])  # 最新价
                prev_close = float(parts[3])  # 昨收价

                if prev_close > 0:
                    change = current - prev_close
                    change_pct = (change / prev_close) * 100
                else:
                    change, change_pct = 0.0, 0.0

                return {
                    "symbol": "DXY",
                    "name": "美元指数",
                    "price": current,
                    "change": round(change, 3),
                    "changePercent": round(change_pct, 2),
                    "high_24h": float(parts[6]) if float(parts[6]) > 0 else None,
                    "low_24h": float(parts[7]) if float(parts[7]) > 0 else None,
                    "open": float(parts[5]) if float(parts[5]) > 0 else current,
                    "previous_close": prev_close,
                    "timestamp": format_iso8601(datetime.now()),
                }
        except Exception as e:
            logger.error(f"Failed to fetch DXY data: {e}")
        return None

    def _fetch_oil(self):
        """获取原油数据（WTI 原油 - 新浪财经 hf_CL）"""
        try:
            url = "https://hq.sinajs.cn/list=hf_CL"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw and len(raw.split('"')[1].split(",")) > 8:
                parts = raw.split('"')[1].split(",")
                current = float(parts[0])  # 最新价
                prev_close = float(parts[8])  # 昨收价

                if prev_close > 0:
                    change = current - prev_close
                    change_pct = (change / prev_close) * 100
                else:
                    change, change_pct = 0.0, 0.0

                return {
                    "symbol": "CL=F",
                    "name": "原油",
                    "price": current,
                    "change": round(change, 3),
                    "changePercent": round(change_pct, 2),
                    "high_24h": float(parts[4]) if float(parts[4]) > 0 else None,
                    "low_24h": float(parts[5]) if float(parts[5]) > 0 else None,
                    "open": float(parts[2]) if float(parts[2]) > 0 else current,
                    "previous_close": prev_close,
                    "timestamp": format_iso8601(datetime.now()),
                }
        except Exception as e:
            logger.error(f"Failed to fetch oil data: {e}")
        return None

    def _fetch_us10y(self):
        """获取美债 10 年期收益率数据（AkShare / 新浪财经 TB10Y）"""
        try:
            url = "https://hq.sinajs.cn/list=TB10Y"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw and len(raw.split('"')[1].split(",")) > 5:
                # 债券格式: ['债券名称', '最新价', '涨跌幅', '昨收', '最高', '最低']
                parts = raw.split('"')[1].split(",")
                current = float(parts[1])
                change_pct = float(parts[2])
                prev_close = float(parts[3])

                return {
                    "symbol": "US10Y",
                    "name": "美债 10Y",
                    "price": round(current, 3),
                    "change": round(current - prev_close, 3),
                    "changePercent": round(change_pct, 2),
                    "high_24h": float(parts[4]) if float(parts[4]) > 0 else None,
                    "low_24h": float(parts[5]) if float(parts[5]) > 0 else None,
                    "open": prev_close,
                    "previous_close": prev_close,
                    "timestamp": format_iso8601(datetime.now()),
                }
        except Exception as e:
            logger.error(f"Failed to fetch US10Y data from Sina: {e}")

        try:
            # Fallback to AkShare
            df = ak.bond_zh_us_rate()
            if df is not None and not df.empty:
                rate_col = next((c for c in df.columns if "10" in c), None)
                if rate_col and len(df) > 1:
                    current = round(float(df.iloc[-1][rate_col]), 3)
                    prev_close = round(float(df.iloc[-2][rate_col]), 3)
                    change = current - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close > 0 else 0.0
                    return {
                        "symbol": "US10Y",
                        "name": "美债 10Y",
                        "price": current,
                        "change": round(change, 3),
                        "changePercent": round(change_pct, 2),
                        "high_24h": None,
                        "low_24h": None,
                        "open": current,
                        "previous_close": prev_close,
                        "timestamp": format_iso8601(datetime.now()),
                    }
        except Exception as e:
            logger.error(f"Failed to fetch US10Y data fallback: {e}")
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
            "timestamp": None,
        }


# 单例
market_terminal_service = MarketTerminalService()
