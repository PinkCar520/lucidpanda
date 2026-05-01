import re
import json
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
            sh_index_data = self._fetch_shanghai_index()
            sz_index_data = self._fetch_shenzhen_index()

            data = {
                "gold": gold_data or self._empty_quote("XAU", "伦敦金"),
                "gold_cny": gold_cny_data or self._empty_quote("AU9999", "上海金"),
                "dxy": dxy_data or self._empty_quote("DXY", "美元指数"),
                "oil": oil_data or self._empty_quote("CL=F", "WTI原油"),
                "us10y": us10y_data or self._empty_quote("US10Y", "美债 10Y"),
                "sh_index": sh_index_data or self._empty_quote("000001.SH", "上证指数"),
                "sz_index": sz_index_data or self._empty_quote("399001.SZ", "深证成指"),
                "last_updated": format_iso8601(datetime.now()),
            }

            self._cache["market_snapshot"] = {"data": data, "timestamp": now}
            return data

        except Exception as e:
            logger.error(f"Failed to fetch market snapshot: {e}")
            return None

    def get_gold_history_24h(self):
        """
        获取金价走势（24h 小时线）。
        采用三重保障方案：东方财富原生现货 -> 国内期货锚定 -> 国际金汇率换算。
        利用 MarketCalendar 智能判断数据时效性。
        """
        from src.lucidpanda.utils.market_calendar import get_market_status
        from zoneinfo import ZoneInfo
        
        now_utc = datetime.now().astimezone(ZoneInfo("UTC"))
        cache_key = "gold_history_24h"
        
        # 1. 检查有效缓存 (10分钟)
        if cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if (datetime.now() - cache_entry["timestamp"]).total_seconds() < 600:
                return cache_entry["data"]

        # 获取当前各市场状态
        cn_status = get_market_status("CN")
        gold_status = get_market_status("GOLD")
        
        # 定义时区
        tz_sh = ZoneInfo("Asia/Shanghai")
        
        trend = []
        
        # --- 第一重：东方财富 (原生上海金现货) ---
        # 仅在 A 股/上海金交易时段或刚收盘时作为首选
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Referer": "https://quote.eastmoney.com/center/gridlist.html"
            }
            url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=118.AU9999&ut=fa5fd1943c7b386f172d6893dbf24410&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56&klt=60&fqt=1&end=20500101&lmt=48"
            resp = requests.get(url, headers=headers, timeout=5)
            data = resp.json()
            
            if data and data.get("data") and "klines" in data["data"]:
                klines = data["data"]["klines"]
                raw_trend = []
                for item in klines:
                    parts = item.split(",")
                    if len(parts) >= 6:
                        try:
                            # 东方财富返回的是北京时间
                            ts_local = datetime.strptime(parts[0], "%Y-%m-%d %H:%M").replace(tzinfo=tz_sh)
                            raw_trend.append({
                                "timestamp": format_iso8601(ts_local),
                                "price": round(float(parts[2]), 2),
                                "is_forecast": False
                            })
                        except Exception: continue
                
                if raw_trend:
                    last_ts_utc = ts_local.astimezone(ZoneInfo("UTC"))
                    # 动态阈值：开市要求 1.5h 内，休市要求 16h 内（覆盖夜盘到次日开盘）
                    threshold = 5400 if cn_status != "CLOSED" else 57600
                    if (now_utc - last_ts_utc).total_seconds() < threshold:
                        logger.info(f"✅ Gold history fetched via EastMoney (Market: {cn_status})")
                        trend = raw_trend[-24:]
                    else:
                        logger.warning(f"⚠️ EastMoney data too old: {last_ts_utc.isoformat()}, fallback...")
        except Exception as e:
            logger.warning(f"⚠️ EastMoney gold history failed: {e}")

        if not trend:
            # --- 第二重：国内黄金期货 (au0) 形状锚定 ---
            try:
                df = ak.futures_zh_minute_sina(symbol="au0", period="60")
                if df is not None and not df.empty:
                    recent = df.tail(24)
                    current_spot = self._fetch_gold_cny()
                    current_spot_price = current_spot.get("price", 0) if current_spot else 0
                    
                    price_offset = 0.0
                    if current_spot_price > 0:
                        last_futures_price = float(recent.iloc[-1]["close"])
                        price_offset = current_spot_price - last_futures_price
                    
                    raw_trend = []
                    for _, row in recent.iterrows():
                        try:
                            ts_val = row["datetime"]
                            # 新浪期货分钟线通常也是北京时间
                            ts_obj = datetime.strptime(ts_val, "%Y-%m-%d %H:%M:%S") if isinstance(ts_val, str) else ts_val
                            ts_local = ts_obj.replace(tzinfo=tz_sh)
                            raw_trend.append({
                                "timestamp": format_iso8601(ts_local),
                                "price": round(float(row["close"]) + price_offset, 2),
                                "is_forecast": False
                            })
                        except Exception: continue
                    
                    if raw_trend:
                        last_ts_utc = ts_local.astimezone(ZoneInfo("UTC"))
                        threshold = 5400 if cn_status != "CLOSED" else 57600
                        if (now_utc - last_ts_utc).total_seconds() < threshold:
                            logger.info(f"✅ Gold history fetched via Sina Futures (Market: {cn_status})")
                            trend = raw_trend
                        else:
                            logger.warning(f"⚠️ Sina Futures data too old: {last_ts_utc.isoformat()}, fallback...")
            except Exception as e:
                logger.warning(f"⚠️ Sina Futures gold history failed: {e}")

        if not trend:
            # --- 第三重：yfinance (国际金走势) ---
            # 在国内休市或数据异常时，这是最可靠的实时源
            try:
                import yfinance as yf
                import time
                import random
                
                # 如果之前有过 Rate Limit 报错，这里加一个随机微小延迟避开并发冲突
                time.sleep(random.uniform(0.1, 0.5))
                
                gold = yf.Ticker("GC=F")
                # 再次尝试，增加重试逻辑
                df = None
                for attempt in range(2):
                    try:
                        df = gold.history(period="3d", interval="1h", timeout=10)
                        if df is not None and not df.empty:
                            break
                    except Exception:
                        if attempt == 0: time.sleep(1)
                
                if df is not None and not df.empty:
                    recent = df.tail(24)
                    current_spot = self._fetch_gold_cny()
                    current_price = current_spot.get("price", 0) if current_spot else 0
                    
                    scale_factor = 0.128 
                    if current_price > 0:
                        last_intl = float(recent.iloc[-1]["Close"])
                        if last_intl > 0:
                            scale_factor = current_price / last_intl
                    
                    raw_trend = []
                    for ts, row in recent.iterrows():
                        # yfinance 的 index 通常带时区 (UTC)
                        ts_utc = ts.astimezone(ZoneInfo("UTC"))
                        raw_trend.append({
                            "timestamp": format_iso8601(ts_utc),
                            "price": round(float(row["Close"]) * scale_factor, 2),
                            "is_forecast": False
                        })
                    if raw_trend:
                        last_ts_utc = ts_utc
                        threshold = 7200 if gold_status != "CLOSED" else 86400
                        if (now_utc - last_ts_utc).total_seconds() < threshold:
                            logger.info(f"✅ Gold history fetched via yfinance (Market: {gold_status})")
                            trend = raw_trend
                        else:
                            logger.warning(f"⚠️ yfinance data too old: {last_ts_utc.isoformat()}")
            except Exception as e:
                logger.error(f"❌ All gold history sources failed: {e}")
        
        # 3. 最终处理：保存有效数据到缓存，或降级使用陈旧缓存
        if trend:
            self._cache[cache_key] = {"data": trend, "timestamp": datetime.now()}
            return trend
        elif cache_key in self._cache:
            logger.warning("⚠️ Using STALE cache as a last resort")
            return self._cache[cache_key]["data"]
            
        return []

    def _fetch_gold_cny(self):
        """获取上海金数据 (AU9999) - 新浪财经"""
        try:
            url = "http://hq.sinajs.cn/list=gds_AU9999"
            headers = {"Referer": "http://finance.sina.com.cn"}
            resp = requests.get(url, headers=headers, timeout=5)
            if resp.status_code == 200:
                # 解析格式: var hq_str_gds_AU9999="current,?,buy,sell,high,low,time,prev_close,open,...";
                match = re.search(r'hq_str_gds_AU9999="([^"]+)"', resp.text)
                if match:
                    parts = match.group(1).split(",")
                    if len(parts) > 8:
                        price = float(parts[0])
                        prev_close = float(parts[7])
                        if prev_close > 0:
                            change = price - prev_close
                            change_pct = (change / prev_close) * 100
                        else:
                            change, change_pct = 0.0, 0.0

                        return {
                            "symbol": "AU9999",
                            "name": "上海金",
                            "price": round(price, 2),
                            "change": round(change, 2),
                            "changePercent": round(change_pct, 2),
                            "timestamp": format_iso8601(datetime.now())
                        }
            return None
        except Exception as e:
            logger.error(f"Failed to fetch gold_cny: {e}")
            return None

    def _fetch_gold(self):
        """获取黄金数据（伦敦金现货 - 对标国际基准）"""
        try:
            url = "https://hq.sinajs.cn/list=hf_XAU"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw and len(raw.split('"')[1].split(",")) > 8:
                parts = raw.split('"')[1].split(",")
                current = float(parts[0])  # 最新价
                prev_close = float(parts[8])  # 昨日收盘价

                if prev_close > 0:
                    change = current - prev_close
                    change_pct = (change / prev_close) * 100
                else:
                    change, change_pct = 0.0, 0.0

                return {
                    "symbol": "XAU",
                    "name": "伦敦金",
                    "price": current,
                    "change": round(change, 2),
                    "changePercent": round(change_pct, 2),
                    "high_24h": float(parts[4]) if float(parts[4]) > 0 else None,
                    "low_24h": float(parts[5]) if float(parts[5]) > 0 else None,
                    "open": float(parts[2]) if float(parts[2]) > 0 else current,
                    "previous_close": prev_close,
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
                    "name": "WTI原油",
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

    def _fetch_shanghai_index(self):
        """获取上证指数实时数据（新浪财经 s_sh000001）"""
        try:
            url = "https://hq.sinajs.cn/list=s_sh000001"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw:
                payload = raw.split('"')[1]
                parts = payload.split(",")
                # 常见格式: 名称, 最新价, 涨跌额, 涨跌幅, 成交量(手), 成交额(元)
                if len(parts) >= 4:
                    price = float(parts[1])
                    change = float(parts[2])
                    change_pct = float(parts[3])
                    prev_close = price - change
                    return {
                        "symbol": "000001.SH",
                        "name": "上证指数",
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "changePercent": round(change_pct, 2),
                        "high_24h": None,
                        "low_24h": None,
                        "open": None,
                        "previous_close": round(prev_close, 2) if prev_close > 0 else None,
                        "timestamp": format_iso8601(datetime.now()),
                    }
        except Exception as e:
            logger.error(f"Failed to fetch Shanghai index data: {e}")
        return None

    def _fetch_shenzhen_index(self):
        """获取深证成指实时数据（新浪财经 s_sz399001）"""
        try:
            url = "https://hq.sinajs.cn/list=s_sz399001"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw:
                payload = raw.split('"')[1]
                parts = payload.split(",")
                if len(parts) >= 4:
                    price = float(parts[1])
                    change = float(parts[2])
                    change_pct = float(parts[3])
                    prev_close = price - change
                    return {
                        "symbol": "399001.SZ",
                        "name": "深证成指",
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "changePercent": round(change_pct, 2),
                        "high_24h": None,
                        "low_24h": None,
                        "open": None,
                        "previous_close": round(prev_close, 2) if prev_close > 0 else None,
                        "timestamp": format_iso8601(datetime.now()),
                    }
        except Exception as e:
            logger.error(f"Failed to fetch Shenzhen index data: {e}")
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
