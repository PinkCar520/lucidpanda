import re
import json
from datetime import datetime, timedelta

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
        self._cache_ttl = 30  # Increase to 30s to reduce backend pressure

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
            # Parallel fetch or sequential - for now we stick to implementation but with cache protection
            # Add small random jitter if multiple requests arrive at exact same time with empty cache
            import time
            import random
            time.sleep(random.uniform(0.01, 0.05))
            
            # Re-check cache after jitter
            if "market_snapshot" in self._cache:
                entry = self._cache["market_snapshot"]
                if now - entry["timestamp"] < self._cache_ttl:
                    return entry["data"]

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

    def get_gold_history_24h(self, force_refresh: bool = False):
        """
        获取金价走势（24h 小时线）。
        统一以国际伦敦金 (XAU) 为基准，确保与顶部报价一致。
        """
        cache_key = "gold_history_24h"

        # 1. 检查有效缓存 (30秒 - 紧跟实时报价)
        if not force_refresh and cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if (datetime.now() - cache_entry["timestamp"]).total_seconds() < 30:
                return cache_entry["data"]

        # 统一使用 get_gold_history_intl_custom("1h") 的结果
        trend = self.get_gold_history_intl_custom("1h", force_refresh=force_refresh)

        if trend:
            self._cache[cache_key] = {"data": trend, "timestamp": datetime.now()}
        return trend

    def get_gold_history_intl_custom(self, granularity: str = "1h", force_refresh: bool = False):
        """
        获取国际金价走势，支持不同粒度的深度定制。
        返回格式: {"history": [...], "pre_close": float}
        """
        import requests
        from zoneinfo import ZoneInfo
        from datetime import datetime, timedelta

        cache_key = f"gold_history_intl_{granularity}"
        if not force_refresh and cache_key in self._cache:
            cache_entry = self._cache[cache_key]
            if (datetime.now() - cache_entry["timestamp"]).total_seconds() < 900:
                return cache_entry["data"]

        result = {"history": [], "pre_close": None}

        # 获取上一交易日收盘价 (作为分时图基准)
        pre_close = None
        try:
            daily_url = "https://stock2.finance.sina.com.cn/futures/api/json.php/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=XAU"
            daily_resp = requests.get(daily_url, timeout=5)
            daily_data = daily_resp.json()
            if daily_data and len(daily_data) >= 2:
                pre_close = float(daily_data[-2]["close"])
        except Exception: pass
        result["pre_close"] = pre_close

        # --- 1m/1h: 使用 Sina MinLine (1分钟线) ---
        if granularity in ["1m", "1h"]:
            try:
                # Sina 国际金 1 分钟线 (当日)
                url = "https://stock.finance.sina.com.cn/futures/api/json_v2.php/GlobalFuturesService.getGlobalFuturesMinLine?symbol=XAU"
                resp = requests.get(url, timeout=10)
                data = resp.json()
                if data and isinstance(data, dict):
                    key = list(data.keys())[0]
                    all_points_raw = data[key]
                    if all_points_raw:
                        point_map = {}
                        for p in all_points_raw:
                            ts_str = p[-1]
                            price = p[1]
                            if ts_str and price:
                                try:
                                    # 显式使用 Asia/Shanghai，format_iso8601 会将其转为 UTC
                                    ts_obj = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                                    point_map[ts_obj] = round(float(price), 2)
                                except Exception: continue

                        sorted_times = sorted(point_map.keys())

                        # 如果是 1m，返回全量点 (不采样)
                        if granularity == "1m":
                            full_trend = []
                            for t in sorted_times:
                                full_trend.append({
                                    "timestamp": format_iso8601(t),
                                    "price": point_map[t],
                                    "is_forecast": False
                                })
                            if full_trend:
                                result["history"] = full_trend
                                self._cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                                return result

                        # 如果是 1h，采样为 24 个点
                        sampled_trend = []
                        if sorted_times:
                            last_time = sorted_times[-1]
                            for i in range(24):
                                target_time = last_time - timedelta(hours=i)
                                # 寻找最接近 target_time 的点
                                best_match = None
                                min_diff = 3600
                                for t in reversed(sorted_times):
                                    diff = abs((t - target_time).total_seconds())
                                    if diff < min_diff:
                                        min_diff = diff
                                        best_match = t
                                    if diff > 7200: break

                                if best_match:
                                    sampled_trend.insert(0, {
                                        "timestamp": format_iso8601(best_match),
                                        "price": point_map[best_match],
                                        "is_forecast": False
                                    })

                        if sampled_trend:
                            result["history"] = sampled_trend
                            self._cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                            return result
            except Exception as e:
                logger.error(f"❌ Gold 1m/1h history fetch failed: {e}")

        # --- 15m/30m: 使用 Sina MiniKLine15m (15分钟线) / 5MLine (采样) ---
        elif granularity == "15m":
            try:
                url = "https://stock2.finance.sina.com.cn/futures/api/json.php/GlobalFuturesService.getGlobalFuturesMiniKLine15m?symbol=XAU"
                resp = requests.get(url, timeout=10)
                data = resp.json() 
                if data and isinstance(data, list):
                    points = []
                    for item in data:
                        try:
                            ts_obj = datetime.strptime(item[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                            # 归一化：如果价格是标准价 (~2300)，乘以 2 匹配 Sina MinLine 规模
                            def normalize(v):
                                val = float(v)
                                return round(val * 2 if val < 3000 else val, 2)

                            points.append({
                                "timestamp": format_iso8601(ts_obj),
                                "open": normalize(item[1]),
                                "high": normalize(item[2]),
                                "low": normalize(item[3]),
                                "price": normalize(item[4]), # Close
                                "is_forecast": False
                            })
                        except Exception: continue
                    if points:
                        result["history"] = points[-96:] # 最近 24 小时
                        self._cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                        return result
            except Exception as e:
                logger.error(f"❌ Gold 15m history fetch failed: {e}")

        elif granularity == "30m":
            try:
                url = "https://stock2.finance.sina.com.cn/futures/api/json.php/GlobalFuturesService.getGlobalFuturesMiniKLine30m?symbol=XAU"
                resp = requests.get(url, timeout=10)
                data = resp.json() 
                if data and isinstance(data, list):
                    points = []
                    for item in data:
                        try:
                            ts_obj = datetime.strptime(item[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                            def normalize(v):
                                val = float(v)
                                return round(val * 2 if val < 3000 else val, 2)

                            points.append({
                                "timestamp": format_iso8601(ts_obj),
                                "open": normalize(item[1]),
                                "high": normalize(item[2]),
                                "low": normalize(item[3]),
                                "price": normalize(item[4]), # Close
                                "is_forecast": False
                            })
                        except Exception: continue
                    if points:
                        result["history"] = points[-96:] 
                        self._cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                        return result
            except Exception as e:
                logger.error(f"❌ Gold 30m history fetch failed: {e}")

        # --- 4h: 使用 Sina 60MLine (60分钟线) 采样 ---
        elif granularity == "4h":
            try:
                url = "https://stock2.finance.sina.com.cn/futures/api/json.php/GlobalFuturesService.getGlobalFuturesMiniKLine60m?symbol=XAU"
                resp = requests.get(url, timeout=10)
                data = resp.json() 
                if data and isinstance(data, list):
                    points = []
                    for item in data:
                        try:
                            ts_obj = datetime.strptime(item[0], "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                            def normalize(v):
                                val = float(v)
                                return round(val * 2 if val < 3000 else val, 2)

                            points.append({
                                "timestamp": ts_obj,
                                "open": normalize(item[1]),
                                "high": normalize(item[2]),
                                "low": normalize(item[3]),
                                "price": normalize(item[4]) # Close price
                            })
                        except Exception: continue

                    # 采样：每 4 小时取一个点 (00:00, 04:00, 08:00...)
                    points.sort(key=lambda x: x["timestamp"])
                    sampled_trend = []
                    if points:
                        for p in points:
                            if p["timestamp"].hour % 4 == 0:
                                sampled_trend.append({
                                    "timestamp": format_iso8601(p["timestamp"]),
                                    "open": p["open"],
                                    "high": p["high"],
                                    "low": p["low"],
                                    "price": p["price"],
                                    "is_forecast": False
                                })

                        last_real_ts = points[-1]["timestamp"]
                        if sampled_trend and sampled_trend[-1]["timestamp"] != format_iso8601(last_real_ts):
                            sampled_trend.append({
                                "timestamp": format_iso8601(last_real_ts),
                                "open": points[-1]["open"],
                                "high": points[-1]["high"],
                                "low": points[-1]["low"],
                                "price": points[-1]["price"],
                                "is_forecast": False
                            })

                    if sampled_trend:
                        result["history"] = sampled_trend[-180:]
                        self._cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                        return result
            except Exception as e:
                logger.error(f"❌ Gold 4h history fetch failed: {e}")

        # --- 1d: 使用 Sina DailyKLine (日线) ---
        elif granularity == "1d":
            try:
                url = "https://stock2.finance.sina.com.cn/futures/api/json.php/GlobalFuturesService.getGlobalFuturesDailyKLine?symbol=XAU"
                resp = requests.get(url, timeout=10)
                data = resp.json() 
                if data and isinstance(data, list):
                    limit_dt = datetime.now() - timedelta(days=60)
                    trend = []
                    for item in data:
                        try:
                            ts_obj = datetime.strptime(item["date"], "%Y-%m-%d").replace(tzinfo=ZoneInfo("Asia/Shanghai"))
                            if ts_obj >= limit_dt.replace(tzinfo=ZoneInfo("Asia/Shanghai")):
                                def normalize(v):
                                    val = float(v)
                                    return round(val * 2 if val < 3000 else val, 2)

                                trend.append({
                                    "timestamp": format_iso8601(ts_obj),
                                    "open": normalize(item["open"]),
                                    "high": normalize(item["high"]),
                                    "low": normalize(item["low"]),
                                    "price": normalize(item["close"]),
                                    "is_forecast": False
                                })
                        except Exception: continue

                    if trend:
                        result["history"] = trend
                        self._cache[cache_key] = {"data": result, "timestamp": datetime.now()}
                        return result

            except Exception as e:
                logger.error(f"❌ Gold 1d history fetch failed: {e}")

        return result
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
        """获取黄金数据（统一使用伦敦金期货 XAU 接口 - 2倍报价对齐）"""
        try:
            # 弃用不稳定的 fx_sxauusd，统一改用与走势图相同的 XAU 期货接口
            url = "https://hq.sinajs.cn/list=hf_XAU"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn"}
            )
            raw = resp.text
            if '="' in raw:
                # 格式: var hq_str_hf_XAU="price,?,buy,sell,high,low,time,prev_close,open,?,?...";
                match = re.search(r'hq_str_hf_XAU="([^"]+)"', raw)
                if match:
                    parts = match.group(1).split(",")
                    current = float(parts[0])
                    prev_close = float(parts[7])
                    
                    change = current - prev_close
                    change_pct = (change / prev_close) * 100 if prev_close > 0 else 0.0

                    return {
                        "symbol": "XAU/USD",
                        "name": "伦敦金",
                        "price": round(current, 2),
                        "change": round(change, 2),
                        "changePercent": round(change_pct, 2),
                        "high_24h": float(parts[4]) if float(parts[4]) > 0 else None,
                        "low_24h": float(parts[5]) if float(parts[5]) > 0 else None,
                        "open": float(parts[8]) if float(parts[8]) > 0 else (prev_close + change),
                        "previous_close": prev_close,
                        "timestamp": format_iso8601(datetime.now()),
                    }
        except Exception as e:
            logger.error(f"Failed to fetch unified London Gold (XAU): {e}")
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
        """获取美债 10 年期收益率数据（使用 Sina globalbd_us10yt 或 AkShare）"""
        import math
        
        def safe_float(val, default=0.0):
            try:
                f = float(val)
                return f if math.isfinite(f) else default
            except (ValueError, TypeError):
                return default

        # 1. 尝试新浪 globalbd_us10yt (美国10年期国债收益率 - 高可靠源)
        try:
            url = "https://hq.sinajs.cn/list=globalbd_us10yt"
            resp = requests.get(
                url, timeout=5, headers={"Referer": "https://finance.sina.com.cn/"}
            )
            raw = resp.text
            if '="' in raw:
                content = raw.split('"')[1]
                parts = content.split(",")
                if len(parts) >= 14:
                    current = safe_float(parts[1])
                    prev_close = safe_float(parts[2])
                    
                    change = current - prev_close
                    change_pct = ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

                    return {
                        "symbol": "US10Y",
                        "name": "美债 10Y",
                        "price": round(current, 3),
                        "change": round(change, 3),
                        "changePercent": round(change_pct, 2),
                        "high_24h": safe_float(parts[4]) if safe_float(parts[4]) > 0 else None,
                        "low_24h": safe_float(parts[5]) if safe_float(parts[5]) > 0 else None,
                        "open": prev_close,
                        "previous_close": prev_close,
                        "timestamp": format_iso8601(datetime.now()),
                    }
        except Exception as e:
            logger.warning(f"Sina globalbd_us10yt failed: {e}")

        # 2. 尝试 AkShare (准确但稍慢)
        try:
            df = ak.bond_zh_us_rate()
            if df is not None and not df.empty:
                rate_col = next((c for c in df.columns if "美国" in c and "10年" in c and "收益率" in c and "-" not in c), None)
                if not rate_col:
                    rate_col = next((c for c in df.columns if "US" in c and "10" in c and "Yield" in c), None)
                
                if rate_col:
                    valid_data = df[df[rate_col].notna()]
                    if not valid_data.empty:
                        last_row = valid_data.iloc[-1]
                        current = safe_float(last_row[rate_col])
                        
                        prev_close = current
                        if len(valid_data) > 1:
                            prev_close = safe_float(valid_data.iloc[-2][rate_col])
                        
                        change = current - prev_close
                        change_pct = ((current - prev_close) / prev_close * 100) if prev_close > 0 else 0.0

                        return {
                            "symbol": "US10Y",
                            "name": "美债 10Y",
                            "price": round(current, 3),
                            "change": round(change, 3),
                            "changePercent": round(change_pct, 2),
                            "high_24h": None,
                            "low_24h": None,
                            "open": prev_close,
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
            "timestamp": format_iso8601(datetime.now()),
        }


# 单例
market_terminal_service = MarketTerminalService()
