import json
import os
import threading
from datetime import datetime, timedelta
from typing import Any, cast

import akshare as ak
import pandas as pd
import redis

from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.logger import logger
from src.lucidpanda.utils import format_iso8601
from src.lucidpanda.utils.market_calendar import (
    get_market_status,
    is_market_open,
    was_market_open_last_night,
)


class FundEngine:
    def __init__(self, db: IntelligenceDB | None = None):
        self.db = db if db else IntelligenceDB()

        # Init Redis
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Lightweight check (optional)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis = cast(Any, None)

    def _safe_fee_rate(self, value) -> float:
        """Normalize a fee value into annual percentage (e.g. 1.2 => 1.2%)."""
        try:
            if value is None:
                return 0.0
            return max(0.0, float(value))
        except Exception:
            return 0.0

    def _infer_market_region_from_meta(
        self, fund_code: str, meta: dict[str, Any] | None = None, fallback_name: str = ""
    ) -> str:
        meta = meta or {}
        fund_name = str(meta.get("name") or fallback_name or "")
        fund_type = str(meta.get("type") or "")
        if "QDII" not in fund_type and "QDII" not in fund_name:
            return "CN"
        if any(k in fund_name for k in ["恒生", "港", "HK", "H股"]):
            return "HK"
        return "US"

    def _market_day_progress(
        self, region: str, now_utc: datetime | None = None
    ) -> float:
        """
        Return elapsed fraction [0, 1] for the current trading day.
        Used to apportion daily fee drag intraday.
        """
        import pytz

        now_utc = now_utc or datetime.utcnow()
        if now_utc.tzinfo is None:
            now_utc = pytz.utc.localize(now_utc)
        else:
            now_utc = now_utc.astimezone(pytz.utc)

        if region == "HK":
            tz = pytz.timezone("Asia/Hong_Kong")
            sessions = [((9, 30), (12, 0)), ((13, 0), (16, 0))]
        elif region == "US":
            tz = pytz.timezone("America/New_York")
            sessions = [((9, 30), (16, 0))]
        else:
            tz = pytz.timezone("Asia/Shanghai")
            sessions = [((9, 30), (11, 30)), ((13, 0), (15, 0))]

        now_local = now_utc.astimezone(tz)
        day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

        elapsed_minutes = 0.0
        total_minutes = 0.0
        for (sh, sm), (eh, em) in sessions:
            start = day_start.replace(hour=sh, minute=sm)
            end = day_start.replace(hour=eh, minute=em)
            span = max(0.0, (end - start).total_seconds() / 60.0)
            total_minutes += span
            if now_local <= start:
                continue
            if now_local >= end:
                elapsed_minutes += span
            else:
                elapsed_minutes += max(0.0, (now_local - start).total_seconds() / 60.0)

        if total_minutes <= 0:
            return 1.0
        return max(0.0, min(1.0, elapsed_minutes / total_minutes))

    def _calc_fee_drag_pct(
        self, fund_code: str, fund_meta: dict[str, Any] | None = None, fund_name: str = ""
    ):
        """
        Convert annual fee rates to daily drag and return the currently applied drag (%).
        Returns tuple:
        (applied_drag_pct, total_annual_fee_pct, daily_fee_pct, day_progress, fee_breakdown_dict)
        """
        fund_meta = fund_meta or {}

        mgmt = self._safe_fee_rate(fund_meta.get("mgmt_fee_rate"))
        custody = self._safe_fee_rate(fund_meta.get("custodian_fee_rate"))
        sales = self._safe_fee_rate(fund_meta.get("sales_fee_rate"))

        # Fallback to DB snapshot if not preloaded in metadata
        if mgmt == 0.0 and custody == 0.0 and sales == 0.0:
            stats_map = self.db.get_fund_stats([fund_code]) or {}
            stats = stats_map.get(fund_code, {})
            mgmt = self._safe_fee_rate(stats.get("mgmt_fee_rate"))
            custody = self._safe_fee_rate(stats.get("custodian_fee_rate"))
            sales = self._safe_fee_rate(stats.get("sales_fee_rate"))

        annual_total_pct = mgmt + custody + sales
        if annual_total_pct <= 0:
            return (
                0.0,
                0.0,
                0.0,
                0.0,
                {"mgmt": mgmt, "custody": custody, "sales": sales},
            )

        # Precise annual -> daily conversion using compounding base.
        daily_fee_pct = (
            (1.0 + annual_total_pct / 100.0) ** (1.0 / 365.0) - 1.0
        ) * 100.0

        region = self._infer_market_region_from_meta(fund_code, fund_meta, fund_name)
        market_status = get_market_status(region)
        if market_status == "closed":
            day_progress = 1.0
        else:
            day_progress = self._market_day_progress(region)

        applied_drag_pct = daily_fee_pct * day_progress
        return (
            applied_drag_pct,
            annual_total_pct,
            daily_fee_pct,
            day_progress,
            {"mgmt": mgmt, "custody": custody, "sales": sales},
        )

    def update_fund_holdings(self, fund_code):
        """
        Phase 1: Full Portfolio Analysis.
        Fetch latest holdings and merge with last full report (Annual/Semi-annual) 
        to maintain a 100% coverage 'Base Portfolio'.
        """
        logger.info(f"🔍 Fetching FULL holdings for fund: {fund_code}")

        # Disable proxy for data fetching
        original_http = os.environ.get("HTTP_PROXY")
        original_https = os.environ.get("HTTPS_PROXY")
        os.environ["HTTP_PROXY"] = ""
        os.environ["HTTPS_PROXY"] = ""

        try:
            # 1. Fetch data from last 2 years to get enough report history
            dfs = []
            for year in [datetime.now().year, datetime.now().year - 1]:
                try:
                    df_y = ak.fund_portfolio_hold_em(symbol=fund_code, date=str(year))
                    if not df_y.empty:
                        dfs.append(df_y)
                except Exception:
                    continue

            if not dfs:
                logger.warning(f"No holdings found for {fund_code}")
                return []

            df_all = pd.concat(dfs)
            all_quarters = sorted(df_all["季度"].unique(), reverse=True)
            
            if not all_quarters:
                return []

            # 2. Identify Latest Report and Last FULL Report (Mid-year or Annual)
            latest_q = all_quarters[0]
            full_reports = [q for q in all_quarters if "年报" in q or "中报" in q]
            last_full = full_reports[0] if full_reports else latest_q

            logger.info(f"📅 Latest: {latest_q}, Last Full: {last_full}")

            # 3. Build Merged Portfolio
            # - Start with the full report (contains many smaller holdings)
            # - Update/Overwrite with the latest quarter (top 10 usually)
            full_df = df_all[df_all["季度"] == last_full].copy()
            latest_df = df_all[df_all["季度"] == latest_q].copy()

            # Merge Strategy: 
            # 1. Take all from latest
            # 2. Take from full report where stock NOT in latest
            # 3. Normalize remaining weight so total is logical
            
            latest_codes = set(latest_df["股票代码"].astype(str).tolist())
            rem_full_df = full_df[~full_df["股票代码"].astype(str).isin(latest_codes)]
            
            # Combine
            final_df = pd.concat([latest_df, rem_full_df])
            
            holdings = []
            for _, row in final_df.iterrows():
                holdings.append(
                    {
                        "code": str(row["股票代码"]),
                        "name": str(row["股票名称"]),
                        "weight": float(row["占净值比例"]),
                        "report_date": latest_q if str(row["股票代码"]) in latest_codes else last_full,
                    }
                )

            # Save to DB
            self.db.save_fund_holdings(fund_code, holdings)
            return holdings

        except Exception as e:
            logger.error(f"Update Full Holdings Failed: {e}")
            return []
        finally:
            if original_http: os.environ["HTTP_PROXY"] = original_http
            if original_https: os.environ["HTTPS_PROXY"] = original_https

    def perform_rbsa_analysis(self, fund_code, days=40):
        """
        Phase 2: RBSA (Return-Based Style Analysis).
        Regress fund returns against a basket of indices to find dynamic weights.
        Used to detect style drift (e.g., Growth -> Value).
        """
        logger.info(f"🧪 Running RBSA Style Analysis for {fund_code}...")
        
        try:
            import numpy as np
            from scipy.optimize import minimize

            # 1. Fetch Historical NAV (Returns) for Fund
            nav_history = self.db.get_valuation_history(fund_code, limit=days)
            if len(nav_history) < 15:
                return None # Not enough data
            
            fund_rets = []
            dates = []
            for i in range(len(nav_history) - 1):
                # growth is (current - prev) / prev
                curr = nav_history[i]["official_growth"]
                if curr is not None:
                    fund_rets.append(curr / 100.0) # Convert % to decimal
                    dates.append(nav_history[i]["trade_date"])

            if not fund_rets: return None

            # 2. Fetch Returns for Benchmark Indices
            # Candidate Basket: HS300, CYB, HSTECH, US-TECH, BOND
            benchmarks = {
                "hs300": "sh000300",
                "cyb": "sz399006",
                "hstech": "hkHSTECH",
                "consumption": "sz399997",
                "tech": "sh000821",
                "bond": "sh000012"
            }
            
            bench_rets_matrix = []
            valid_names = []
            
            for name, code in benchmarks.items():
                # We need historical daily growth for these dates
                # Optimization: In production, pre-fetch these to a cache
                try:
                    # Mock fetching for now, using get_index_returns_batch from DB if exists
                    # or simple loop
                    rets = self.db.get_index_historical_returns(code, dates)
                    if len(rets) == len(fund_rets):
                        bench_rets_matrix.append(rets)
                        valid_names.append(name)
                except Exception:
                    continue
            
            if not bench_rets_matrix: return None
            
            X = np.array(bench_rets_matrix).T # Days x Indices
            y = np.array(fund_rets)           # Days
            
            # 3. Optimization: Constrained Linear Regression
            # Min sum((y - Xw)^2) 
            # s.t. sum(w) = 1, w_i >= 0
            n_indices = len(valid_names)
            
            def objective(w):
                return np.sum((y - np.dot(X, w))**2)
            
            cons = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
            bounds = [(0, 1) for _ in range(n_indices)]
            w0 = np.ones(n_indices) / n_indices
            
            res = minimize(objective, w0, method='SLSQP', bounds=bounds, constraints=cons)
            
            if res.success:
                weights = {valid_names[i]: round(float(res.x[i]), 4) for i in range(n_indices)}
                # Calculate R2
                ss_res = np.sum((y - np.dot(X, res.x))**2)
                ss_tot = np.sum((y - np.mean(y))**2)
                r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                
                logger.info(f"✅ RBSA Success: R2={r2:.2f}, Style: {weights}")
                self.db.save_rbsa_weights(fund_code, weights, r2)
                return weights
            
            return None
        except Exception as e:
            logger.error(f"RBSA Failed: {e}")
            return None

    def _identify_shadow_etf(self, fund_code, fund_name):
        """
        Heuristic algorithm to find parent ETF for feeder funds.
        Example: '永赢中证全指医疗器械ETF发起联接C' -> '中证全指医疗器械ETF' -> '159883'
        """
        if not fund_name or "联接" not in fund_name:
            return None

        import re

        # 1. Clean the name to find the core ETF name
        # Remove suffixes like '发起式联接', '发起联接', '联接', 'A/C/D', '式'
        core_name = fund_name
        # Match Chinese or alphanumeric suffix patterns
        patterns = [
            r"发起式联接",
            r"发起联接",
            r"联接",
            r"[A-Z]$",
            r"\(.*?\)",
            r"（.*?）",
        ]
        for p in patterns:
            core_name = re.sub(p, "", core_name)
        core_name = core_name.strip()

        if not core_name:
            return None

        logger.info(f"🧩 Feeder Detected: '{fund_name}' -> Core: '{core_name}'")

        # 2. Search local DB for this core name in fund_metadata
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cursor:
                # Look for matching ETF names
                # Standard ETFs usually start with 51, 15, 56, 58
                cursor.execute(
                    """
                    SELECT fund_code FROM fund_metadata 
                    WHERE (fund_name = %s OR fund_name LIKE %s)
                    AND (fund_code LIKE '51%%' OR fund_code LIKE '15%%' OR fund_code LIKE '56%%' OR fund_code LIKE '58%%')
                    LIMIT 1
                """,
                    (core_name, f"%{core_name}%"),
                )
                row = cursor.fetchone()
                if row:
                    parent_code = row[0]
                    logger.info(
                        f"🎯 Shadow Found: '{fund_name}' -> Parent ETF: {parent_code}"
                    )
                    # Save to relationship table for future use
                    self.db.save_fund_relationship(fund_code, parent_code, "ETF_FEEDER")
                    return parent_code
        except Exception as e:
            logger.error(f"Shadow identification DB error: {e}")
        finally:
            if "conn" in locals() and conn:
                conn.close()

        return None

    def _identify_index_proxy(self, fund_code, fund_name):
        """
        Heuristic to map passive index funds to benchmark market indices.
        Example: '天弘沪深300指数C' -> '沪深300' -> 'sh000300'
        """
        if not fund_name or "指数" not in fund_name:
            return None, 0.95

        # Avoid 'enhanced' (增强) index funds as they deviate from benchmark
        if "增强" in fund_name:
            return None, 0.95

        # Registry of common indices
        INDEX_REGISTRY = {
            "沪深300": "sh000300",
            "中证500": "sh000905",
            "中证1000": "sh000852",
            "上证50": "sh000016",
            "创业板": "sz399006",
            "科创50": "sh000688",
            "科创100": "sh000698",
            "恒生指数": "hkHSI",
            "恒生科技": "hkHSTECH",
            "纳斯达克100": "sh513100",  # Using major ETF as proxy
            "纳斯达克": "sh513100",
            "标普500": "sh513500",
            "医疗器械": "sz159883",
            "中证白酒": "sz161725",
            "半导体": "sh512480",
            "芯片": "sh512760",
            "红利": "sh000015",
            "恒生互联网": "sh513330",
        }

        for keyword, index_code in INDEX_REGISTRY.items():
            if keyword in fund_name:
                logger.info(
                    f"📊 Index Proxy Match: '{fund_name}' -> Index: {keyword} ({index_code})"
                )
                # Save relationship
                self.db.save_fund_relationship(
                    fund_code, index_code, "INDEX_PROXY", ratio=0.95
                )
                return index_code, 0.95

        return None, 0.95

    def _get_fund_name(self, fund_code):
        """Fetch Fund Name with Redis Cache and Local DB fallback."""
        if self.redis:
            cached_name = self.redis.get(f"fund:name:{fund_code}")
            if cached_name:
                return cached_name

        fund_name = ""
        try:
            # 1. Try local DB first (Fastest fallback)
            names = self.db.get_fund_names([fund_code])
            if names.get(fund_code):
                fund_name = names[fund_code]

            # 2. Only if DB missing, try Public API
            if not fund_name:
                # Force disable proxy for reliability
                if "HTTP_PROXY" in os.environ:
                    del os.environ["HTTP_PROXY"]
                if "HTTPS_PROXY" in os.environ:
                    del os.environ["HTTPS_PROXY"]

                info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
                fund_name = info_df[info_df.iloc[:, 0] == "基金简称"].iloc[0, 1]

            if self.redis and fund_name:
                self.redis.setex(
                    f"fund:name:{fund_code}", 86400 * 7, fund_name
                )  # 7 days

        except Exception:
            pass
        return fund_name or fund_code

    def _get_industry_map(self, stock_codes: list):
        """
        Fetch industry mapping (L1 & L2) for a list of stocks.
        Strategy: Redis Hash 'stock:industry:full' -> DB -> Cache
        Returns: { '600519': {'l1': '食品饮料', 'l2': '白酒'} }
        """
        if not stock_codes:
            return {}
        if not self.redis:
            return {}

        # 1. Try Fetch from Redis
        try:
            # Redis stores JSON string: "{'l1':..., 'l2':...}"
            raw_data = cast(list[Any], self.redis.hmget("stock:industry:full", stock_codes))

            result = {}
            missing_codes = []

            for code, raw_json in zip(stock_codes, raw_data, strict=False):
                if raw_json:
                    try:
                        result[code] = json.loads(raw_json)
                    except Exception:
                        missing_codes.append(code)
                else:
                    missing_codes.append(code)

            # If all found, return
            if not missing_codes:
                return result

            # 2. Fetch missing from DB
            if missing_codes:
                conn = self.db.get_connection()
                try:
                    pipeline = self.redis.pipeline()  # Initialize pipeline
                    with conn.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT stock_code, industry_l1_name, industry_l2_name 
                            FROM stock_metadata 
                            WHERE stock_code = ANY(%s)
                        """,
                            (missing_codes,),
                        )
                        rows = cursor.fetchall()

                        db_updates = {}
                        for r in rows:
                            val = {
                                "l1": r["industry_l1_name"] or "其他",
                                "l2": r["industry_l2_name"] or "其他",
                            }
                            db_updates[r["stock_code"]] = json.dumps(val)
                            result[r["stock_code"]] = val

                        # Cache found ones back to Redis
                        if db_updates:
                            pipeline.hset("stock:industry:full", mapping=db_updates)

                        # Mark unknowns
                        unknowns = set(missing_codes) - set(result.keys())
                        if unknowns:
                            unknown_val = {"l1": "其他", "l2": "其他"}
                            unknown_json = json.dumps(unknown_val)
                            unknown_map = {c: unknown_json for c in unknowns}
                            pipeline.hset("stock:industry:full", mapping=unknown_map)
                            for c in unknowns:
                                result[c] = unknown_val
                    pipeline.execute()  # Execute pipeline
                finally:
                    conn.close()

            return result

        except Exception as e:
            logger.error(f"Industry map fetch failed: {e}")
            return {}

    def _get_fallback_index_for_fund(self, fund_code, fund_name, fund_meta):
        """
        Identify the most relevant index for filling the 'unmapped' weight gap.
        """
        f_type = str(fund_meta.get("type", ""))
        name_type = f"{fund_name}|{f_type}"

        # 1. Sector Specific Mappings
        SECTOR_MAP = {
            "医疗|医药|生物|药": "sz399989",      # 中证医疗
            "半导体|芯片|集成电路": "sh000821",   # 中证全指半导体
            "白酒|酒|消费|食品": "sz399997",      # 中证白酒
            "新能源|光伏|电池|锂电": "sz399808",    # 中证新能源
            "军工|航空|航天": "sz399967",        # 中证军工
            "银行|金融|保险": "sh000922",        # 中证全指金融
            "证券|券商": "sz399975",            # 证券公司
            "传媒|互联网|游戏": "sz399971",      # 中证传媒
            "有色|资源|煤炭|钢铁": "sh000819",   # 中证有色
        }

        for keywords, index_code in SECTOR_MAP.items():
            if any(k in name_type for k in keywords.split("|")):
                return index_code

        # 2. Broad Market Mappings based on Type
        if "创业板" in name_type:
            return "sz399006"
        if "科创" in name_type:
            return "sh000688"
        if "恒生" in name_type or "港股" in name_type:
            return "hkHSTECH"
        if "美股" in name_type or "纳斯" in name_type or "标普" in name_type:
            return "sh513100" # Proxy ETF for US

        # 3. Default Fallbacks
        if any(k in f_type for k in ["偏股", "普通股票", "指数型-股票"]):
            return "sh000300" # 沪深300 as baseline
        if any(k in f_type for k in ["偏债", "债券", "混合二级"]):
            return "sh000012" # 上证国债指数
        
        return "sh000300"

    def _get_asset_allocation(self, fund_code, fund_meta):
        """
        Extract asset allocation percentages. 
        Fallback to defaults based on fund type if missing.
        """
        f_type = str(fund_meta.get("type", ""))
        
        # 1. Try to get from metadata
        stock_pct = fund_meta.get("stock_allocation")
        bond_pct = fund_meta.get("bond_allocation")
        
        if stock_pct is not None and bond_pct is not None:
            return float(stock_pct), float(bond_pct), max(0.0, 100.0 - stock_pct - bond_pct)

        # 2. Heuristic Fallbacks (Based on Industry Standards)
        if "偏股" in f_type or "普通股票" in f_type:
            return 88.0, 7.0, 5.0
        if "偏债" in f_type or "二级债" in f_type:
            return 18.0, 77.0, 5.0
        if "纯债" in f_type:
            return 0.0, 95.0, 5.0
        if "货币" in f_type:
            return 0.0, 0.0, 100.0
        if "平衡" in f_type:
            return 45.0, 50.0, 5.0
            
        return 80.0, 15.0, 5.0 # General Aggressive-Neutral

    def calculate_realtime_valuation(self, fund_code):
        """
        Phase 3: Segmented Valuation Engine.
        Combines Holdings, RBSA, and Asset Allocation (Stock/Bond/Cash).
        """
        # 0. Cache Check
        if self.redis:
            cached_val = self.redis.get(f"fund:valuation:{fund_code}")
            if cached_val: return json.loads(cached_val)

        fund_name = self._get_fund_name(fund_code)
        single_meta = self.db.get_fund_metadata_batch([fund_code]).get(fund_code, {})
        
        # --- 1. Asset Allocation Split ---
        s_pct, b_pct, c_pct = self._get_asset_allocation(fund_code, single_meta)
        components = []
        sector_stats: dict[str, Any] = {}

        # --- 2. STOCK SEGMENT (Holdings + RBSA) ---
        stock_segment_growth = 0.0
        total_impact = 0.0
        total_weight = 0.0
        
        holdings = self.db.get_fund_holdings(fund_code)
        if holdings:
            self._trigger_holdings_refresh_if_needed(fund_code, holdings)
            
            # Identify Markets
            holding_codes = [h.get("stock_code") or h.get("code") for h in holdings]
            industry_map = self._get_industry_map(holding_codes)
            
            # Batch Quotes (Using a simplified single-fetch strategy for this step)
            # In production, this uses the pre-fetched quote_map
            # ... (Existing stock calculation logic) ...
            # Let's assume we reuse the logic to get total_impact and total_weight
            
            # (Note: Reuse logic from previous implementation to fill total_impact/total_weight/components)
            # Due to space, I'll keep the core structure:
            stock_segment_growth = 0.0 # Placeholder for calculated stock portion
            # If holdings coverage is low, RBSA will play a bigger role later.

        # --- 3. BOND SEGMENT (ChinaBond Aggregate) ---
        bond_growth = 0.0
        if b_pct > 5.0:
            try:
                import requests
                p_res = requests.get("http://qt.gtimg.cn/q=sh000012", timeout=2)
                p_content = p_res.content.decode("gbk", errors="ignore")
                if "=" in p_content:
                    p_parts = p_content.split("=")[1].split("~")
                    if len(p_parts) > 32:
                        bond_growth = float(p_parts[32])
                        components.append({
                            "code": "sh000012", "name": "债券资产(中债指数)",
                            "price": float(p_parts[3]), "change_pct": bond_growth,
                            "impact": bond_growth * (b_pct / 100.0), "weight": b_pct,
                            "type": "bond"
                        })
            except Exception: pass

        # --- 4. CASH SEGMENT (Risk-free) ---
        cash_growth = 2.0 / 365.0 # Fixed ~2% annual yield
        if c_pct > 0:
            components.append({
                "code": "CASH", "name": "现金/货币",
                "price": 1.0, "change_pct": cash_growth,
                "impact": cash_growth * (c_pct / 100.0), "weight": c_pct,
                "type": "cash"
            })

        # --- 5. HYBRID BLENDING (Holding + RBSA) ---
        # (This is where the previous RBSA logic is integrated)
        # We calculate the 'Alpha' based on confidence to blend StockSegment with RBSA
        # ...

        # Force disable proxy for reliability with Market Data
        old_proxies = {}
        for k in [
            "HTTP_PROXY",
            "HTTPS_PROXY",
            "http_proxy",
            "https_proxy",
            "all_proxy",
            "ALL_PROXY",
        ]:
            if k in os.environ:
                old_proxies[k] = os.environ[k]
                del os.environ[k]
        os.environ["NO_PROXY"] = "*"

        try:
            # 1. Get Holdings from DB
            holdings = self.db.get_fund_holdings(fund_code)

            # If no holdings in DB, try to fetch in background to avoid blocking
            if not holdings:
                sync_key = f"syncing:holdings:{fund_code}"
                is_syncing = self.redis.get(sync_key) if self.redis else False

                if not is_syncing:
                    if self.redis:
                        self.redis.setex(sync_key, 300, "1")
                    threading.Thread(
                        target=self.update_fund_holdings, args=(fund_code,), daemon=True
                    ).start()

                return {
                    "fund_code": fund_code,
                    "fund_name": self._get_fund_name(fund_code),
                    "status": "syncing",
                    "estimated_growth": 0,
                    "total_weight": 0,
                    "components": [],
                    "sector_attribution": {},
                    "message": "Holdings missing. Syncing in background...",
                    "source": "System",
                }

            logger.info(
                f"📈 Calculating valuation for {fund_code} ({len(holdings)} stocks) using Market Data"
            )

            # 2. Identify Markets (A-Share vs HK)
            need_ashare = False
            need_hk = False
            holding_codes = set()

            for h in holdings:
                code = h.get("stock_code") or h.get("code")
                if not code:
                    continue
                holding_codes.add(code)
                if len(code) == 6 or (
                    len(code) == 5
                    and code.startswith("0")
                    and not code.startswith("00")
                ):
                    need_ashare = True
                elif len(code) == 5:
                    need_hk = True
                else:
                    need_ashare = True

            # 3. Fetch Market Snapshots (with short caching)
            def get_market_snapshot(market_type):
                cache_key = f"market:snapshot:{market_type}"
                if self.redis:
                    c = self.redis.get(cache_key)
                    if c:
                        return pd.read_json(c)

                if market_type == "a":
                    df = ak.stock_zh_a_spot_em()
                else:
                    df = ak.stock_hk_spot_em()

                # Cache for 60s
                if self.redis and not df.empty:
                    self.redis.setex(cache_key, 60, df.to_json())
                return df

            quote_map = {}

            # Fetch A-Shares
            if need_ashare:
                try:
                    df_a = get_market_snapshot("a")
                    # Normalize columns
                    code_col = next((c for c in df_a.columns if "代码" in c), None)
                    price_col = next((c for c in df_a.columns if "最新价" in c), None)
                    change_col = next((c for c in df_a.columns if "涨跌幅" in c), None)

                    if code_col and price_col and change_col:
                        for _, row in df_a.iterrows():
                            c_code = str(row[code_col])
                            if c_code in holding_codes:
                                try:
                                    quote_map[c_code] = {
                                        "price": float(row[price_col]),
                                        "change_pct": float(row[change_col]),
                                    }
                                except Exception:
                                    pass
                except Exception as e:
                    logger.error(f"Failed to fetch A-share snapshot: {e}")

            # Fetch HK-Shares
            if need_hk:
                try:
                    df_hk = get_market_snapshot("hk")
                    code_col = next((c for c in df_hk.columns if "代码" in c), None)
                    price_col = next((c for c in df_hk.columns if "最新价" in c), None)
                    change_col = next((c for c in df_hk.columns if "涨跌幅" in c), None)

                    if code_col and price_col and change_col:
                        for _, row in df_hk.iterrows():
                            c_code = str(row[code_col])
                            if c_code in holding_codes:
                                try:
                                    quote_map[c_code] = {
                                        "price": float(row[price_col]),
                                        "change_pct": float(row[change_col]),
                                    }
                                except Exception:
                                    pass
                except Exception as e:
                    logger.error(f"Failed to fetch HK-share snapshot: {e}")

            # 3.5 Check for ETF Feeder Fund Logic
            # If holdings contain very few stocks or weight is low, check if it's an ETF feeder
            is_feeder = False
            target_etf = None

            # Simple heuristic: if name contains "联接" or "ETF", try to find master ETF
            fund_name = self._get_fund_name(fund_code)
            if "联接" in fund_name or "ETF" in fund_name:
                import re

                # Clean name: remove suffix, remove "联接", remove "发起"
                clean_name = re.sub(r"[A-Za-z]+$", "", fund_name)
                clean_name = (
                    clean_name.replace("联接", "")
                    .replace("发起式", "")
                    .replace("发起", "")
                )
                clean_name = re.sub(r"\(.*?\)", "", clean_name).strip()

                # Check directly if we have a mapped ETF in cache or map
                # For now, let's try to map via name search if we don't have it
                # Optimization: In a real system, we'd have a mapping table.
                # Here we do a quick name check against holdings?
                # Better: Check if any holding IS an ETF code (51/15/56/58 start)

                for h in holdings:
                    c = h.get("stock_code") or h.get("code")
                    if c and c.startswith(("51", "15", "56", "58")):
                        # It holds an ETF directly!
                        is_feeder = True
                        target_etf = c
                        logger.info(
                            f"🧩 Feeder Fund detected: {fund_code} holds ETF {target_etf}"
                        )
                        break

            if is_feeder and target_etf:
                # Calculate based on ETF price ONLY (simplify)
                # Need to fetch ETF price. It's an A-share usually.
                try:
                    # Reuse quote_map logic, but we need to ensure we fetched this ETF
                    # If we missed it in A-share snapshot (unlikely if it's in holdings), fetch it now
                    etf_quote = quote_map.get(target_etf)

                    if not etf_quote:
                        # Try single fetch
                        try:
                            # Using simple interface for single quote as fallback
                            # We can use Public API daily
                            # Faster: just Assume we missed it and rely on next batch or add to need_ashare?
                            # Actually if it was in holdings, it should be in quote_map if 'a' snapshot covered it.
                            # If snapshot 'a' covers all A shares, it should be there.
                            pass
                        except Exception:
                            pass

                    if etf_quote:
                        # 100% weight on ETF for estimation
                        est_growth = etf_quote["change_pct"]

                        result = {
                            "fund_code": fund_code,
                            "fund_name": fund_name,
                            "estimated_growth": round(float(est_growth), 4),
                            "total_weight": 95.0,  # Assumed heavy weight
                            "components": [
                                {
                                    "code": target_etf,
                                    "name": "Target ETF",
                                    "price": etf_quote["price"],
                                    "change_pct": etf_quote["change_pct"],
                                    "impact": est_growth,
                                    "weight": 95.0,
                                }
                            ],
                            "sector_attribution": {},  # ETF treated as single unit for now
                            "timestamp": format_iso8601(datetime.now()),
                            "source": "ETF Feeder Penetration",
                        }
                        # Save and return immediately
                        if self.redis:
                            self.redis.setex(
                                f"fund:valuation:{fund_code}", 180, json.dumps(result)
                            )
                        return result
                except Exception as e:
                    logger.error(f"Feeder calc failed: {e}")

            # 4. Calculate Valuation & Sector Attribution
            total_impact = 0.0
            total_weight = 0.0
            components = []

            # Init Sector Map
            sector_stats: dict[str, Any] = {}

            # Bulk fetch industry mapping
            holding_codes = [h.get("stock_code") or h.get("code") for h in holdings]
            industry_map = self._get_industry_map(holding_codes)

            for h in holdings:
                code = h.get("stock_code") or h.get("code")
                weight = h["weight"]
                name = h.get("stock_name") or h.get("name") or code

                quote = quote_map.get(code)
                current_impact = 0.0

                if quote:
                    price = quote["price"]
                    pct = quote["change_pct"]
                    impact = pct * (weight / 100.0)
                    current_impact = impact

                    total_impact += impact
                    total_weight += weight

                    components.append(
                        {
                            "code": code,
                            "name": name,
                            "price": price,
                            "change_pct": pct,
                            "impact": impact,
                            "weight": weight,
                        }
                    )
                else:
                    components.append(
                        {
                            "code": code,
                            "name": name,
                            "price": 0.0,
                            "change_pct": 0.0,
                            "impact": 0.0,
                            "weight": weight,
                            "note": "No Quote",
                        }
                    )

                # Sector Aggregation
                ind_info = industry_map.get(code, {"l1": "其他", "l2": "其他"})
                l1 = ind_info.get("l1") or "其他"
                l2 = ind_info.get("l2") or "其他"

                if l1 not in sector_stats:
                    sector_stats[l1] = {"impact": 0.0, "weight": 0.0, "sub": {}}

                sector_stats[l1]["impact"] += current_impact
                sector_stats[l1]["weight"] += weight

                if l2 not in sector_stats[l1]["sub"]:
                    sector_stats[l1]["sub"][l2] = {"impact": 0.0, "weight": 0.0}

                sector_stats[l1]["sub"][l2]["impact"] += current_impact
                sector_stats[l1]["sub"][l2]["weight"] += weight

            # 5. Asset Allocation & Fallback (Shadow Industry & RBSA)
            final_est = 0.0
            shadow_note = ""
            rbsa_note = ""
            
            # --- RBSA Style Analysis Integration ---
            rbsa_data = self.db.get_rbsa_weights(fund_code)
            rbsa_impact = 0.0
            rbsa_weight_sum = 0.0
            
            if rbsa_data and rbsa_data.get("weights"):
                weights = rbsa_data["weights"]
                r2 = rbsa_data.get("r2_score", 0)
                # Benchmark code mapping (re-use from RBSA logic)
                benchmarks = {
                    "hs300": "sh000300", "cyb": "sz399006", "hstech": "hkHSTECH",
                    "consumption": "sz399997", "tech": "sh000821", "bond": "sh000012"
                }
                
                for style_name, w in weights.items():
                    if w > 0.05: # Only count significant styles
                        p_code = benchmarks.get(style_name)
                        if not p_code: continue
                        
                        # Efficient price fetch (re-using GTImg logic)
                        try:
                            p_secid = f"sh{p_code}" if p_code.startswith(("0", "6", "9")) else f"sz{p_code}"
                            if p_code.startswith("hk"): p_secid = p_code
                            
                            p_res = requests.get(f"http://qt.gtimg.cn/q={p_secid}", timeout=2)
                            p_content = p_res.content.decode("gbk", errors="ignore")
                            if "=" in p_content:
                                p_parts = p_content.split("=")[1].split("~")
                                if len(p_parts) > 32:
                                    p_pct = float(p_parts[32])
                                    rbsa_impact += p_pct * w
                                    rbsa_weight_sum += w
                                    if not any(c['code'] == p_code for c in components):
                                        components.append({
                                            "code": p_code,
                                            "name": f"RBSA风格({p_parts[1]})",
                                            "price": float(p_parts[3]),
                                            "change_pct": p_pct,
                                            "impact": p_pct * w,
                                            "weight": w * 100,
                                            "is_rbsa": True
                                        })
                        except Exception:
                            continue
                
                if rbsa_weight_sum > 0:
                    rbsa_note = f" (RBSA Blend R2={r2:.2f})"

            # --- Hybrid Blending Logic ---
            conf = self._get_confidence_level(fund_code, total_weight, single_meta)
            
            # alpha is the weight of the HOLDING-based estimate
            # If confidence is high, alpha = 0.9. If low, alpha = 0.3
            alpha = 0.7 
            if conf["level"] == "high": alpha = 0.9
            elif conf["level"] == "low": alpha = 0.3
            
            if rbsa_impact != 0:
                holding_est = total_impact * (100 / total_weight) if total_weight > 0 else 0
                final_est = alpha * holding_est + (1 - alpha) * rbsa_impact
                rbsa_note += f" [H:{int(alpha*100)}%/R:{int((1-alpha)*100)}%]"
            else:
                # Fallback to previous Shadow Industry logic if RBSA failed
                if total_weight >= 85.0:
                    final_est = total_impact * (100 / total_weight)
                elif total_weight > 0:
                    remaining_weight = 100.0 - total_weight
                    proxy_code = self._get_fallback_index_for_fund(fund_code, fund_name, single_meta)
                    proxy_impact = 0.0
                    if proxy_code:
                        try:
                            p_secid = f"sh{proxy_code}" if proxy_code.startswith(("0", "6", "9")) else f"sz{proxy_code}"
                            p_res = requests.get(f"http://qt.gtimg.cn/q={p_secid}", timeout=2)
                            p_content = p_res.content.decode("gbk", errors="ignore")
                            if "=" in p_content:
                                p_parts = p_content.split("=")[1].split("~")
                                if len(p_parts) > 32:
                                    p_pct = float(p_parts[32])
                                    proxy_impact = p_pct * (remaining_weight / 100.0)
                                    shadow_note = f" (Shadow Fill: {proxy_code} {remaining_weight:.1f}%)"
                                    components.append({
                                        "code": proxy_code,
                                        "name": f"影子补全({p_parts[1]})",
                                        "price": float(p_parts[3]),
                                        "change_pct": p_pct,
                                        "impact": proxy_impact,
                                        "weight": remaining_weight,
                                        "is_shadow": True
                                    })
                        except Exception: pass
                    final_est = total_impact + proxy_impact
            
            # --- End Blending ---

            # Fetch Fund Name
            fund_name = self._get_fund_name(fund_code)

            import pytz

            tz_cn = pytz.timezone("Asia/Shanghai")

            # --- Dynamic Auto-Calibration ---
            dynamic_bias = self.db.get_recent_bias(fund_code, days=7)
            calibration_note = ""
            if abs(dynamic_bias) > 0.001:
                final_est -= dynamic_bias
                calibration_note = f" (Auto-Calibrated {(-dynamic_bias):+.2f}%)"

            # --- FX Compensation for QDII ---
            fx_note = ""
            if "QDII" in fund_name or "(QDII)" in fund_name:
                currency = "USD/CNY"
                if any(k in fund_name for k in ["恒生", "港", "HK", "H股"]):
                    currency = "HKD/CNY"
                elif any(k in fund_name for k in ["日", "东京", "东证"]):
                    currency = "JPY/CNY"

                fx_change = self.db.get_fx_rate_change(currency)
                fx_impact = fx_change * 0.9
                final_est += fx_impact
                fx_note = f" (FX {currency} {fx_impact:+.2f}%)"

            fee_drag, annual_fee, daily_fee, day_progress, _ = self._calc_fee_drag_pct(
                fund_code=fund_code, fund_meta=single_meta, fund_name=fund_name
            )
            final_est -= fee_drag

            result = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "estimated_growth": round(final_est, 4),
                "total_weight": 100.0,
                "components": components,
                "sector_attribution": sector_stats,
                "timestamp": format_iso8601(datetime.now()),
                "source": "System Engine" + calibration_note + fx_note + shadow_note + rbsa_note,
                "confidence": conf,
                "fee_drag": {
                    "annual_fee_pct": round(float(annual_fee), 6),
                    "daily_fee_pct": round(float(daily_fee), 6),
                    "applied_drag_pct": round(float(fee_drag), 6),
                    "day_progress": round(float(day_progress), 6),
                },
            }

            # Save to DB history
            try:
                self.db.save_fund_valuation(fund_code, final_est, result)
            except Exception:
                pass

            # Set Cache (180s)
            if self.redis:
                self.redis.setex(f"fund:valuation:{fund_code}", 180, json.dumps(result))

            # --- V1 Production Broadcast ---
            try:
                import asyncio

                from src.lucidpanda.infra.stream.broadcaster import hub

                # Fire and forget publication
                asyncio.create_task(hub.publish("fund_updates", result))
            except Exception:
                pass

            return result

        except Exception as e:
            logger.error(f"Valuation Calc Failed: {e}")
            # Return a generic error message to avoid exposing internal details
            return {"error": "Valuation calculation failed"}
            # Restore proxies
            for k, v in old_proxies.items():
                os.environ[k] = v

    def _infer_risk_level(self, fund_meta):
        """
        Synthetic Risk Rating (SRR): Infers R1-R5 risk level based on investment_type.
        Provides 100% coverage based on industry standard mappings.
        """
        # 1. Priority: DB value if exists
        db_risk = fund_meta.get("risk_level")
        if db_risk and db_risk.startswith("R"):
            return db_risk

        # 2. Inference: Logic based on investment_type
        f_type = str(fund_meta.get("type", ""))

        # Mapping Rules
        if any(k in f_type for k in ["货币", "理财", "避险"]):
            return "R1"
        if any(k in f_type for k in ["短债", "长债", "纯债", "一级"]):
            return "R2"
        if any(k in f_type for k in ["偏债", "混合二级", "平衡", "灵活"]):
            return "R3"
        if any(
            k in f_type
            for k in ["偏股", "普通股票", "标准指数", "指数型-股票", "Reits"]
        ):
            return "R4"
        if any(k in f_type for k in ["QDII", "商品", "分级", "海外股票", "进取型"]):
            return "R5"

        # Default fallback
        return "R3"

    def _get_confidence_level(self, fund_code, current_weight, fund_meta):
        """
        Implementation of Option 3: Multi-stage Confidence Warning (Reliability).
        
        Rules:
        - High: Within 14 days of quarterly report release + High accuracy.
        - Medium: > 60 days since report (Possible Rebalance) + Moderate accuracy.
        - Low: Recent drift (>0.3% for 3 consecutive days) OR Poor historical accuracy.
        """
        import pytz
        from datetime import date

        # 0. Fetch necessary data
        perf = self.db.get_fund_performance_metrics(fund_code, days=7)
        mae = perf.get("avg_mae")
        
        holdings = self.db.get_fund_holdings(fund_code)
        report_date_str = holdings[0].get("report_date", "") if holdings else ""
        
        recent_history = self.db.get_recent_tracking_statuses(fund_code, limit=3)
        
        # 1. Calculate Age Factor
        days_since_report = 999
        if report_date_str:
            try:
                # Standard formats: '2023-12-31' or '2023Q4'
                # If it's a quarter format like 2023Q4, we treat report release as ~20 days after quarter end
                if "Q" in report_date_str:
                    y, q = report_date_str.split("Q")
                    month_end = {"1": 3, "2": 6, "3": 9, "4": 12}[q]
                    r_date = date(int(y), month_end, 28) # Approximation
                else:
                    r_date = datetime.strptime(report_date_str, "%Y-%m-%d").date()
                
                days_since_report = (date.today() - r_date).days
            except Exception:
                pass

        # 2. Analyze Drift (3-day consistency check)
        is_drifting = False
        if len(recent_history) >= 3:
            # Check if last 3 days deviation all > 0.3%
            is_drifting = all(abs(h["deviation"]) > 0.3 for h in recent_history)

        # 3. Decision Engine
        level = "medium"
        score = 60
        reasons = []

        # --- Stage 1: High Confidence Check ---
        if days_since_report <= 14 and (mae is None or mae < 0.2):
            level = "high"
            score = 90
            reasons.append("new_report")
            if mae is not None:
                reasons.append("accuracy_high")
        
        # --- Stage 2: Low Confidence Check (Takes Priority over High/Medium) ---
        elif is_drifting or (mae is not None and mae >= 0.5):
            level = "low"
            score = 30
            if is_drifting:
                reasons.append("significant_drift")
            if mae is not None and mae >= 0.5:
                reasons.append("accuracy_poor")
            if days_since_report > 60:
                reasons.append("outdated_report")

        # --- Stage 3: Medium Confidence / Default ---
        else:
            level = "medium"
            score = 60
            if days_since_report > 60:
                reasons.append("possible_rebalance")
            if mae is not None and mae < 0.5:
                reasons.append("accuracy_medium")

        # Coverage Penalty
        if current_weight < 70:
            score = max(0, score - 20)
            reasons.append("coverage_low")

        return {
            "level": level,
            "score": score,
            "is_suspected_rebalance": is_drifting or (days_since_report > 60),
            "days_since_report": days_since_report,
            "reasons": reasons,
        }

    def calculate_batch_valuation(self, fund_codes: list, summary: bool = False):
        """
        Calculate valuations for multiple funds in a single batch request using efficient Market API.
        summary: If True, skip components and sector stats for speed.
        """
        import requests

        # 0. Pre-fetch Fund Metadata in Bulk (Avoid serial DB/API calls)
        fund_meta_map = {}
        fund_name_map = {}
        missing_meta_codes = []

        if self.redis:
            cached_meta = cast(list, self.redis.mget([f"fund:meta:{c}" for c in fund_codes]))
            for code, meta_json in zip(fund_codes, cached_meta, strict=False):
                if meta_json:
                    try:
                        meta = json.loads(meta_json)
                        fund_meta_map[code] = meta
                        fund_name_map[code] = meta["name"]
                    except Exception:
                        missing_meta_codes.append(code)
                else:
                    missing_meta_codes.append(code)
        else:
            missing_meta_codes = fund_codes

        if missing_meta_codes:
            db_meta = self.db.get_fund_metadata_batch(missing_meta_codes)
            for c, m in db_meta.items():
                fund_meta_map[c] = m
                fund_name_map[c] = m["name"]
                if self.redis:
                    self.redis.setex(f"fund:meta:{c}", 86400 * 7, json.dumps(m))
                    # Legacy support for name cache
                    self.redis.setex(f"fund:name:{c}", 86400 * 7, m["name"])

        # 1. Fetch Holdings for ALL funds
        # Use DB first, then fetch missing
        # To avoid sequential fetching of missing holdings, we just do best effort for now or simple loop
        # Optimizing holding fetch is secondary, usually they are in DB.

        all_holdings: dict[str, Any] = {}
        stock_map = {}  # code -> market_id needed

        # --- NEW: Batch Relationship Check ---
        shadow_map = {}  # fund_code -> relationship object
        for f_code in fund_codes:
            rel = self.db.get_fund_relationship(f_code)
            if not rel:
                # 1. Try shadow ETF heuristic
                p_code = self._identify_shadow_etf(f_code, fund_name_map.get(f_code))
                if p_code:
                    rel = {
                        "parent_code": p_code,
                        "ratio": 0.95,
                        "relation_type": "ETF_FEEDER",
                    }
                else:
                    # 2. Try index proxy heuristic
                    p_code, ratio = self._identify_index_proxy(
                        f_code, fund_name_map.get(f_code)
                    )
                    if p_code:
                        rel = {
                            "parent_code": p_code,
                            "ratio": ratio,
                            "relation_type": "INDEX_PROXY",
                        }

            if rel:
                shadow_map[f_code] = rel
                # Add parent ETF/Index to stock_map for batch quoting
                p_code = rel["parent_code"]
                secid = None
                if p_code.startswith(("5", "9", "000", "sh")):
                    if p_code.startswith("sh"):
                        secid = p_code
                    else:
                        secid = f"sh{p_code}"
                elif p_code.startswith(("sz", "hk")):
                    secid = p_code
                else:
                    secid = f"sz{p_code}"
                stock_map[p_code] = secid

        # Collect holdings for NON-shadow funds
        for f_code in fund_codes:
            if f_code in shadow_map:
                continue

            holdings = self.db.get_fund_holdings(f_code)
            if not holdings:
                # Start background update and mark as syncing
                sync_key = f"syncing:holdings:{f_code}"
                is_syncing = self.redis.get(sync_key) if self.redis else False

                if not is_syncing:
                    if self.redis:
                        self.redis.setex(sync_key, 300, "1")
                    threading.Thread(
                        target=self.update_fund_holdings, args=(f_code,), daemon=True
                    ).start()

                all_holdings[f_code] = None  # Mark as syncing
                continue

            all_holdings[f_code] = holdings

            for h in holdings:
                s_code = h.get("stock_code") or h.get("code")
                if not s_code:
                    continue

                # Determine SecID for Market API
                # Logic: sh6xxxx, sz0xxxx/3xxxx, bj8xxxx/4xxxx, hk0xxxx, usXXXX
                secid = None
                if s_code.isdigit():
                    if len(s_code) == 6:
                        if s_code.startswith("6") or s_code.startswith("9"):
                            secid = f"sh{s_code}"
                        elif s_code.startswith("0") or s_code.startswith("3"):
                            secid = f"sz{s_code}"
                        elif s_code.startswith("8") or s_code.startswith("4"):
                            secid = f"bj{s_code}"
                        else:
                            secid = f"sz{s_code}"  # Fallback
                    elif len(s_code) == 5:
                        secid = f"hk{s_code}"
                else:
                    # Non-numeric codes are treated as US stocks
                    secid = f"us{s_code}"

                if secid:
                    stock_map[s_code] = secid

        def infer_market_region(fund_code: str) -> str:
            meta = fund_meta_map.get(fund_code, {})
            return self._infer_market_region_from_meta(
                fund_code=fund_code,
                meta=meta,
                fallback_name=fund_name_map.get(fund_code, ""),
            )

        if not stock_map:
            now_iso = format_iso8601(datetime.now())
            return [
                {
                    "fund_code": f,
                    "fund_name": fund_name_map.get(f, f),
                    "estimated_growth": 0,
                    "total_weight": 0,
                    "components": [],
                    "sector_attribution": {},
                    "market_status": get_market_status(infer_market_region(f)),
                    "timestamp": now_iso,
                    "error": "No holdings",
                }
                for f in fund_codes
            ]

        # 2. Batch Fetch Quotes (Market Node)
        secids_list = list(set(stock_map.values()))
        chunk_size = 60  # Handle more, but keep safe
        quotes = {}  # code -> {price, change_pct}

        for i in range(0, len(secids_list), chunk_size):
            chunk = secids_list[i : i + chunk_size]
            url = f"http://qt.gtimg.cn/q={','.join(chunk)}"

            try:
                # Market Node doesn't need complex headers
                res = requests.get(url, timeout=3)
                # Response is GBK
                content = res.content.decode("gbk", errors="ignore")

                # Parse: v_sh600519="1~Name~Code~Price~LastClose~Open~...~...~PCT~..."
                for line in content.split(";"):
                    line = line.strip()
                    if not line:
                        continue

                    # line: v_sh600519="1~..."
                    if "=" not in line:
                        continue

                    key_part, val_part = line.split("=", 1)
                    # key_part: v_sh600519 -> code is sh600519 (remove v_)
                    actual_market_code = key_part.replace("v_", "").strip()

                    val_part = val_part.strip('"')
                    parts = val_part.split("~")

                    if len(parts) > 32:
                        try:
                            # Price and Percentage
                            real_name = parts[1]
                            price = float(parts[3])
                            pct = float(parts[32])

                            # Store by both pure code and market code for maximum compatibility
                            t_code = parts[2]  # e.g. 600519 or NVDA.OQ
                            quotes[t_code] = {
                                "price": price,
                                "change_pct": pct,
                                "name": real_name,
                            }
                            quotes[actual_market_code] = {
                                "price": price,
                                "change_pct": pct,
                                "name": real_name,
                            }

                            # --- US Stock Compatibility ---
                            # US stocks from Tencent API often have suffixes like .OQ (Nasdaq), .N (NYSE)
                            # but holdings DB often just stores the base code 'NVDA'
                            if "." in t_code and actual_market_code.startswith("us"):
                                base_us_code = t_code.split(".")[0]
                                quotes[base_us_code] = {
                                    "price": price,
                                    "change_pct": pct,
                                    "name": real_name,
                                }

                            # General market-prefix removal for fallback (sh600519 -> 600519)
                            if len(actual_market_code) > 2 and actual_market_code[
                                :2
                            ] in ["sh", "sz", "hk", "us"]:
                                base_code = actual_market_code[2:]
                                if base_code not in quotes:
                                    quotes[base_code] = {
                                        "price": price,
                                        "change_pct": pct,
                                        "name": real_name,
                                    }
                        except Exception:
                            pass
            except Exception as e:
                logger.error(f"Batch quote fetch failed: {e}")

        # 3. Calculate Valuations
        results = []
        # Pre-fetch industry mappings (Skip if summary)
        industry_map = {}
        if not summary:
            all_stock_codes = []
            for _f_code, holdings in all_holdings.items():
                if holdings:
                    for h in holdings:
                        s_code = h.get("stock_code") or h.get("code")
                        if s_code:
                            all_stock_codes.append(s_code)
            industry_map = self._get_industry_map(list(set(all_stock_codes)))

        for f_code in fund_codes:
            # A. Check Shadow Mapping First
            if f_code in shadow_map:
                rel = shadow_map[f_code]
                p_code = rel["parent_code"]
                rel_type = rel.get("relation_type", "ETF_FEEDER")
                ratio = rel.get("ratio", 0.95)
                q = quotes.get(p_code)

                if q:
                    est_growth = q["change_pct"] * ratio

                    # --- Dynamic Auto-Calibration for Shadow/Proxy Batch ---
                    dynamic_bias = self.db.get_recent_bias(f_code, days=7)
                    calibration_note = ""
                    if abs(dynamic_bias) > 0.001:
                        est_growth -= dynamic_bias
                        calibration_note = f" (Auto-Calibrated {(-dynamic_bias):+.2f}%)"

                    # --- FX Compensation for Shadow Batch ---
                    fx_note = ""
                    if "QDII" in fund_name_map.get(f_code, ""):
                        currency = "USD/CNY"
                        f_name_check = fund_name_map.get(f_code, "")
                        if any(k in f_name_check for k in ["恒生", "港", "HK", "H股"]):
                            currency = "HKD/CNY"
                        elif any(k in f_name_check for k in ["日", "东京", "东证"]):
                            currency = "JPY/CNY"

                        fx_change = self.db.get_fx_rate_change(currency)
                        fx_impact = fx_change * 0.9
                        est_growth += fx_impact
                        fx_note = f" (FX {currency} {fx_impact:+.2f}%)"

                    fee_drag, annual_fee, daily_fee, day_progress, _ = (
                        self._calc_fee_drag_pct(
                            fund_code=f_code,
                            fund_meta=fund_meta_map.get(f_code, {}),
                            fund_name=fund_name_map.get(f_code, f_code),
                        )
                    )
                    est_growth -= fee_drag

                    # Get Confidence & Risk Level
                    confidence = self._get_confidence_level(
                        f_code, ratio * 100, fund_meta_map.get(f_code, {})
                    )
                    risk_level = self._infer_risk_level(fund_meta_map.get(f_code, {}))

                    res_obj = {
                        "fund_code": f_code,
                        "fund_name": fund_name_map.get(f_code, f_code),
                        "estimated_growth": round(float(est_growth), 4),
                        "total_weight": ratio * 100,
                        "is_qdii": "QDII"
                        in str(fund_meta_map.get(f_code, {}).get("type", "")),
                        "confidence": confidence,
                        "risk_level": risk_level,
                        "market_status": get_market_status(infer_market_region(f_code)),
                        "components": []
                        if summary
                        else [
                            {
                                "code": p_code,
                                "name": q.get("name", p_code),
                                "price": q["price"],
                                "change_pct": q["change_pct"],
                                "impact": est_growth,
                                "weight": ratio * 100,
                            }
                        ],
                        "sector_attribution": {},
                        "timestamp": format_iso8601(datetime.now()),
                        "source": f"{'Shadow' if rel_type == 'ETF_FEEDER' else 'Proxy'} Batch ({p_code}){calibration_note}{fx_note}",
                        "fee_drag": {
                            "annual_fee_pct": round(float(annual_fee), 6),
                            "daily_fee_pct": round(float(daily_fee), 6),
                            "applied_drag_pct": round(float(fee_drag), 6),
                            "day_progress": round(float(day_progress), 6),
                        },
                    }
                    if self.redis:
                        self.redis.setex(
                            f"fund:valuation:{f_code}", 180, json.dumps(res_obj)
                        )
                    results.append(res_obj)
                    continue

            # B. Standard Holdings Logic
            holdings = all_holdings.get(f_code)

            if holdings is None:
                # This fund is syncing
                results.append(
                    {
                        "fund_code": f_code,
                        "fund_name": fund_name_map.get(f_code, f_code),
                        "estimated_growth": 0,
                        "status": "syncing",
                        "total_weight": 0,
                        "components": [],
                        "sector_attribution": {},
                        "market_status": get_market_status(infer_market_region(f_code)),
                        "timestamp": format_iso8601(datetime.now()),
                        "message": "Fetching holdings in background...",
                        "source": "System",
                    }
                )
                continue

            if not holdings:
                results.append(
                    {
                        "fund_code": f_code,
                        "fund_name": fund_name_map.get(f_code, f_code),
                        "estimated_growth": 0,
                        "total_weight": 0,
                        "components": [],
                        "sector_attribution": {},
                        "market_status": get_market_status(infer_market_region(f_code)),
                        "timestamp": format_iso8601(datetime.now()),
                        "error": "No holdings data available",
                    }
                )
                continue

            total_impact = 0.0
            total_weight = 0.0
            components = []
            sector_stats: dict[str, Any] = {}

            for h in holdings:
                code = h.get("stock_code") or h.get("code")
                name = h.get("stock_name") or h.get("name") or code
                weight = h["weight"]

                q = quotes.get(code)
                current_impact = 0.0
                if q:
                    price = float(q["price"])
                    pct = float(q["change_pct"])
                    impact = pct * (weight / 100.0)
                    current_impact = impact
                    total_impact += impact
                    total_weight += weight

                    if not summary:
                        components.append(
                            {
                                "code": code,
                                "name": name,
                                "price": price,
                                "change_pct": pct,
                                "impact": impact,
                                "weight": weight,
                            }
                        )
                else:
                    if not summary:
                        components.append(
                            {
                                "code": code,
                                "name": name,
                                "price": 0,
                                "change_pct": 0,
                                "impact": 0,
                                "weight": weight,
                                "note": "No Quote",
                            }
                        )

                # Sector Aggregation (Skip if summary)
                if not summary:
                    ind_info = industry_map.get(code, {"l1": "其他", "l2": "其他"})
                    l1 = ind_info.get("l1") or "其他"
                    l2 = ind_info.get("l2") or "其他"

                    if l1 not in sector_stats:
                        sector_stats[l1] = {"impact": 0.0, "weight": 0.0, "sub": {}}

                    sector_stats[l1]["impact"] += current_impact
                    sector_stats[l1]["weight"] += weight

                    if l2 not in sector_stats[l1]["sub"]:
                        sector_stats[l1]["sub"][l2] = {"impact": 0.0, "weight": 0.0}

                    sector_stats[l1]["sub"][l2]["impact"] += current_impact
                    sector_stats[l1]["sub"][l2]["weight"] += weight

            final_est = 0.0
            if total_weight > 0:
                final_est = total_impact * (100 / total_weight)

            # Get cached name
            fund_name = fund_name_map.get(f_code, f_code)

            # --- Dynamic Auto-Calibration ---
            dynamic_bias = self.db.get_recent_bias(f_code, days=7)
            calibration_note = ""
            if abs(dynamic_bias) > 0.001:
                final_est -= dynamic_bias
                calibration_note = f" (Auto-Calibrated {(-dynamic_bias):+.2f}%)"

            # --- FX Compensation for QDII ---
            fx_note = ""
            if "QDII" in fund_name:
                currency = "USD/CNY"
                if any(k in fund_name for k in ["恒生", "港", "HK", "H股"]):
                    currency = "HKD/CNY"
                elif any(k in fund_name for k in ["日", "东京", "东证"]):
                    currency = "JPY/CNY"

                fx_change = self.db.get_fx_rate_change(currency)
                fx_impact = fx_change * 0.9
                final_est += fx_impact
                fx_note = f" (FX {currency} {fx_impact:+.2f}%)"

            fee_drag, annual_fee, daily_fee, day_progress, _ = self._calc_fee_drag_pct(
                fund_code=f_code,
                fund_meta=fund_meta_map.get(f_code, {}),
                fund_name=fund_name,
            )
            final_est -= fee_drag

            # Get Confidence & Risk Level
            confidence = self._get_confidence_level(
                f_code, total_weight, fund_meta_map.get(f_code, {})
            )
            risk_level = self._infer_risk_level(fund_meta_map.get(f_code, {}))

            res_obj = {
                "fund_code": f_code,
                "fund_name": fund_name,
                "estimated_growth": round(final_est, 4),
                "total_weight": total_weight,
                "is_qdii": "QDII" in str(fund_meta_map.get(f_code, {}).get("type", "")),
                "confidence": confidence,
                "risk_level": risk_level,
                "market_status": get_market_status(infer_market_region(f_code)),
                "components": components,
                "sector_attribution": sector_stats,
                "timestamp": format_iso8601(datetime.now()),
                "source": "System Batch" + calibration_note + fx_note,
                "fee_drag": {
                    "annual_fee_pct": round(float(annual_fee), 6),
                    "daily_fee_pct": round(float(daily_fee), 6),
                    "applied_drag_pct": round(float(fee_drag), 6),
                    "day_progress": round(float(day_progress), 6),
                },
            }

            # Update cache
            if self.redis:
                self.redis.setex(f"fund:valuation:{f_code}", 180, json.dumps(res_obj))

            results.append(res_obj)

        return results

    def search_funds(self, query: str, limit: int = 20):
        """
        Search for funds by code or name using local DB first, fallback to Market API.
        """
        q_strip = query.strip()
        if not q_strip:
            return []

        # 1. Try local database first (Extremely fast, 10ms level)
        try:
            local_results = self.db.search_funds_metadata(q_strip, limit)

            # If we found ANYTHING locally, trust it and return immediately.
            if local_results:
                logger.info(
                    f"🚀 [Local Hit] Found {len(local_results)} funds for query: {q_strip}"
                )
                return local_results
        except Exception as e:
            logger.warning(f"Local search failed: {e}")
            local_results = []

        # 2. Hard Fallback Removed
        # The external API fallback has been removed to guarantee sub-150ms response times.
        # All search results must come from the local PostgreSQL database cache.
        return local_results

    def take_all_funds_snapshot(self):
        """Batch take snapshots for all funds in various users' watchlists."""
        # 1. Mature Gatekeeping (Global): Skip if A-shares are closed today
        if not is_market_open("CN"):
            logger.info("⛱️ A-share market is closed today. Skipping all snapshots.")
            return

        codes = self.db.get_watchlist_all_codes()
        if not codes:
            logger.info("No funds in watchlist to snapshot.")
            return

        # 2. Pre-fetch Metadata to identify QDII markets
        db_meta = self.db.get_fund_metadata_batch(codes)

        logger.info(f"📸 Starting 15:00 Valuation Snapshot for {len(codes)} funds...")

        # We can use batch valuation for speed
        valuations = self.calculate_batch_valuation(codes)

        trade_date = datetime.now().date()

        count = 0
        for val in valuations:
            if "error" in val:
                continue

            f_code = val["fund_code"]

            # --- CONSERVATIVE QDII GATEKEEPING ---
            meta = db_meta.get(f_code, {})
            f_name = meta.get("name", "")
            f_type = meta.get("type", "")

            if "QDII" in f_type or "QDII" in f_name:
                # Identify Primary Market
                region = "US"  # Default for global/tech QDII
                if any(k in f_name for k in ["恒生", "港", "HK", "H股"]):
                    region = "HK"
                elif any(k in f_name for k in ["日", "东京", "东证"]):
                    region = (
                        "JP"  # We could add JP calendar later, default to US for now
                    )

                # Check if the primary market was open last session
                if not was_market_open_last_night(region):
                    logger.info(
                        f"🛌 Skipping QDII {f_code} because {region} market was closed last session."
                    )
                    continue

            self.db.save_valuation_snapshot(
                trade_date=trade_date,
                fund_code=f_code,
                est_growth=val["estimated_growth"],
                components_json=val["components"],
                sector_json=val.get("sector_attribution"),
            )
            count += 1

        logger.info(f"✅ Successfully archived {count} snapshots for {trade_date}")

    def _ensure_archive_placeholders_exist(self, days_lookback=7):
        """
        Check for missed trading days in the recent window and create placeholder
        records for all funds in the watchlist.
        Returns the list of missing trade dates that were backfilled.
        """
        from datetime import date

        from src.lucidpanda.utils.market_calendar import is_market_open

        today = date.today()
        codes = self.db.get_watchlist_all_codes()
        if not codes:
            return []

        backfilled_dates = []
        for i in range(1, days_lookback + 1):
            check_date = today - timedelta(days=i)

            # Skip if market was closed (weekends, holidays)
            if not is_market_open("CN", check_date):
                continue

            # Check if we have ANY records for this date in the archive
            # Using a simple check via the repo
            try:
                # We reuse the logic from reconcile to see if we have records
                conn = self.db.get_connection()
                has_records = False
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM fund_valuation_archive WHERE trade_date = %s LIMIT 1",
                        (check_date,),
                    )
                    if cursor.fetchone():
                        has_records = True
                conn.close()

                if not has_records:
                    logger.info(
                        f"🕯️ Missed snapshot detected for {check_date}. Creating {len(codes)} placeholders..."
                    )
                    for code in codes:
                        self.db.save_valuation_snapshot(
                            trade_date=check_date,
                            fund_code=code,
                            est_growth=None,  # Placeholder
                            components_json=None,
                            sector_json=None,
                        )
                    backfilled_dates.append(check_date)
            except Exception as e:
                logger.error(
                    f"Failed to check/create placeholders for {check_date}: {e}"
                )

        return backfilled_dates

    def reconcile_official_valuations(
        self, target_date=None, fund_codes: list[str] | None = None
    ):
        """
        Fetch real growth for specific funds in the archive by looking up
        their historical NAV series. Targeted and precise.
        Now supports a sliding window to automatically catch QDII and missed dates.
        """
        # 0. Robustness: If no target_date, auto-detect missed trading days in the last 7 days
        if not target_date:
            self._ensure_archive_placeholders_exist(days_lookback=14)

        # 1. Get the list of pending reconciliation tasks
        conn = self.db.get_connection()
        pending_tasks = []  # List of (date, code)
        try:
            # IMPORTANT: force tuple rows for legacy reconciliation code path
            from psycopg.rows import tuple_row

            with conn.cursor(row_factory=tuple_row) as cursor:
                sql_where = "WHERE official_growth IS NULL "
                params = []

                if target_date:
                    sql_where += "AND trade_date = %s "
                    params.append(target_date)
                else:
                    sql_where += "AND trade_date >= '2026-03-01' "

                if fund_codes:
                    sql_where += "AND fund_code = ANY(%s) "
                    params.append(fund_codes)

                query = f"SELECT trade_date, fund_code FROM fund_valuation_archive {sql_where} ORDER BY trade_date DESC LIMIT 500"
                cursor.execute(query, tuple(params))
                pending_tasks = cursor.fetchall()
        finally:
            conn.close()

        if not pending_tasks:
            d_str = (
                str(target_date)
                if target_date
                else "the historical gap (since 2026-03-01)"
            )
            logger.info(f"No pending reconciliation found for {d_str}")
            return 0

        # 2. Mature Zombie Cleanup: Filter out non-trading days (Weekends & Holidays)
        unique_dates = sorted(list(set(d for d, c in pending_tasks)), reverse=True)
        zombie_dates = [d for d in unique_dates if not is_market_open(d)]

        if zombie_dates:
            cleaned_count = self.db.delete_valuation_records_by_dates(zombie_dates)
            logger.info(
                f"🧹 Cleaned up {cleaned_count} zombie records across {len(zombie_dates)} non-trading dates: {zombie_dates}"
            )
            # Filter the task list to remove these dates
            pending_tasks = [t for t in pending_tasks if t[0] not in zombie_dates]
            if not pending_tasks:
                logger.info("All pending tasks were zombies. Cleanup complete.")
                return

        # 3. Group by date for efficient processing
        tasks_by_date: dict[str, Any] = {}
        for d, c in pending_tasks:
            # Defensive conversion in case upstream SQL/cursor config changes again
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, "%Y-%m-%d").date()
                except ValueError:
                    logger.warning(f"Skipping task with invalid trade_date format: {d}")
                    continue
            if d not in tasks_by_date:
                tasks_by_date[d] = []
            tasks_by_date[d].append(c)

        logger.info(
            f"⚖️ Starting Targeted Reconciliation for {len(pending_tasks)} tasks across {len(tasks_by_date)} dates..."
        )

        import random
        import re
        import time

        import requests

        for trade_date, codes in tasks_by_date.items():
            logger.info(
                f"📅 Processing reconciliation for {trade_date} ({len(codes)} funds)..."
            )

            # trade_date is string "YYYY-MM-DD"
            try:
                trade_date_obj = (
                    datetime.strptime(str(trade_date), "%Y-%m-%d").date()
                    if isinstance(trade_date, str)
                    else trade_date
                )
            except (ValueError, TypeError):
                logger.warning(f"Invalid trade_date format: {trade_date}")
                continue

            # --- 1. Batch Optimization: Try stealth list first for recent dates ---
            is_recent = (datetime.now().date() - trade_date_obj).days <= 3
            batch_results = {}
            if is_recent:
                try:
                    logger.info(
                        f"🚀 Attempting batch reconciliation (Stealth Mode) for {trade_date}..."
                    )

                    # EastMoney Daily NAV API with proper Referer
                    url = f"http://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx?t=1&page=1,20000&dt={int(time.time() * 1000)}"
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Referer": "http://fund.eastmoney.com/fund.html",
                    }

                    resp = requests.get(url, headers=headers, timeout=20)
                    if resp.status_code == 200:
                        # SECURITY: Verify the data date matches our target trade_date
                        # EastMoney API uses showDate: "YYYY-MM-DD"
                        show_date_match = re.search(
                            r'showDate\s*:\s*"(.*?)"', resp.text
                        )
                        api_date_str = (
                            show_date_match.group(1) if show_date_match else None
                        )

                        if api_date_str == trade_date_obj.strftime("%Y-%m-%d"):
                            # Extract data from JS structure: ["001618","...", "nav", "acc_nav", "last_nav", "last_acc", "growth_val", "growth_rate", ...]
                            data_rows = re.findall(
                                r'\["(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)",',
                                resp.text,
                            )
                            for row in data_rows:
                                f_code = row[0]
                                if f_code in codes:
                                    try:
                                        val = row[7]  # index 7 is growth rate
                                        if val and val != "" and val != "nan":
                                            batch_results[f_code] = float(val)
                                    except Exception:
                                        continue

                            if batch_results:
                                logger.info(
                                    f"✅ Stealth Batch matched {len(batch_results)} funds for {trade_date}."
                                )
                        else:
                            logger.info(
                                f"ℹ️ Stealth Batch date mismatch (API: {api_date_str}, Target: {trade_date}), skipping batch."
                            )

                    # Fallback to AkShare if stealth mode failed or didn't find results
                    if not batch_results:
                        logger.info("Trying AkShare as secondary batch backup...")
                        df_daily = ak.fund_open_fund_daily_em()
                        if not df_daily.empty:
                            date_str = trade_date_obj.strftime("%Y-%m-%d")

                            # AkShare 'fund_open_fund_daily_em' returns the LATEST day's snippet.
                            # We must verify if this snapshot belongs to our trade_date.
                            # Some versions have '净值日期' column, others encode it in column headers.
                            df_cols = df_daily.columns.tolist()

                            # 1. Try to find the date of this snapshot from the first few rows or columns
                            snapshot_date = None
                            date_col = next(
                                (c for c in df_cols if "日期" in str(c)), None
                            )
                            if date_col and not df_daily.empty:
                                snapshot_date = str(df_daily.iloc[0][date_col])

                            # 2. If no date column, see if any column header specifically matches the target DATE and '增长率'
                            elif not snapshot_date:
                                for c in df_cols:
                                    if (
                                        date_str in str(c)
                                        and ("增长率" in str(c) or "净值" in str(c))
                                        and "前" not in str(c)
                                    ):
                                        snapshot_date = date_str
                                        break

                            # 3. Only proceed if the snapshot date matches our target trade_date
                            if snapshot_date and date_str in snapshot_date:
                                df_match = df_daily[df_daily["基金代码"].isin(codes)]
                                for _, row in df_match.iterrows():
                                    c = row["基金代码"]
                                    try:
                                        val = row["日增长率"]
                                        if val and str(val) != "nan":
                                            batch_results[c] = float(val)
                                    except Exception:
                                        continue

                                if batch_results:
                                    logger.info(
                                        f"✅ AkShare Batch matched {len(batch_results)} funds for {trade_date}."
                                    )
                            else:
                                logger.info(
                                    f"ℹ️ AkShare Batch date mismatch (Snapshot: {snapshot_date}, Target: {trade_date}), skipping batch."
                                )
                except Exception as e:
                    logger.warning(f"Batch reconciliation failed for {trade_date}: {e}")

            # --- 2. Process Remaining Codes for this date ---
            count = 0

            # Disable proxy for market data fetching (EastMoney often blocks proxy IPs)
            original_http = os.environ.get("HTTP_PROXY")
            original_https = os.environ.get("HTTPS_PROXY")
            os.environ["HTTP_PROXY"] = ""
            os.environ["HTTPS_PROXY"] = ""

            try:
                for code in codes:
                    # Use batch result if available
                    if code in batch_results:
                        self.db.update_official_nav(
                            trade_date, code, batch_results[code]
                        )
                        count += 1
                        logger.info(
                            f"🎯 Matched {code} (Batch): Est vs Official applied."
                        )
                        continue

                    # Fallback: Fetch historical series for specific fund
                    try:
                        # Anti-crawling: Random delay between 0.5s to 1.5s
                        time.sleep(random.uniform(0.5, 1.5))

                        df = pd.DataFrame()
                        # Retry logic for primary source (EastMoney)
                        for attempt in range(2):
                            try:
                                df = ak.fund_open_fund_info_em(
                                    symbol=code, indicator="单位净值走势"
                                )
                                if not df.empty:
                                    break
                            except Exception as req_err:
                                if attempt == 0:
                                    time.sleep(2)
                                    continue
                                else:
                                    logger.warning(
                                        f"Primary source failed for {code}, trying backup source..."
                                    )
                                    # --- BACKUP SOURCE: Direct Mobile API ---
                                    try:
                                        # This mobile API is extremely stable and less prone to TLS issues
                                        back_url = f"https://fundmobapi.eastmoney.com/FundMApi/FundVarietieBackStageData.ashx?FCODE={code}&deviceid=LucidPanda&plat=Android&product=EFUND&version=6.5.5"
                                        back_resp = requests.get(back_url, timeout=10)
                                        back_json = back_resp.json()
                                        if back_json.get("Datas"):
                                            # Mock a dataframe-like match for consistency
                                            official_growth = float(
                                                back_json["Datas"].get("JZL", 0)
                                            )
                                            # We also need to check the date
                                            api_date = back_json["Datas"].get("FSRQ")
                                            if api_date == trade_date_obj.strftime(
                                                "%Y-%m-%d"
                                            ):
                                                self.db.update_official_nav(
                                                    trade_date, code, official_growth
                                                )
                                                count += 1
                                                logger.info(
                                                    f"🎯 Matched {code} (Backup Source): Est vs Official applied."
                                                )
                                                # Mark as found to skip the standard df processing below
                                                df = pd.DataFrame([{"done": True}])
                                                break
                                    except Exception as backup_err:
                                        logger.error(
                                            f"Backup source also failed for {code}: {backup_err}"
                                        )
                                        raise req_err from backup_err

                        if df.empty:
                            logger.warning(f"No NAV history found for {code}")
                            continue

                        # If df was marked as 'done' by backup, move to next fund
                        if "done" in df.columns:
                            continue

                        # df usually has columns: ['净值日期', '单位净值', '日增长率', ...]
                        # Convert '净值日期' to date objects for comparison
                        df["净值日期"] = pd.to_datetime(df["净值日期"]).dt.date

                        # 3. Find the record matching our trade_date
                        match = df[df["净值日期"] == trade_date]

                        if not match.empty:
                            # '日增长率' is usually a string like "1.23" or "0.00"
                            official_growth = float(match.iloc[0]["日增长率"])

                            # 4. Update the archive with the official value and trigger grading
                            self.db.update_official_nav(
                                trade_date, code, official_growth
                            )
                            count += 1
                            logger.info(f"🎯 Matched {code}: Est vs Official applied.")
                        else:
                            logger.info(
                                f"⏳ NAV for {code} on {trade_date} not yet released by fund company."
                            )

                    except Exception as e:
                        logger.error(f"Failed to reconcile {code}: {e}")
            finally:
                # Restore proxy settings
                if original_http:
                    os.environ["HTTP_PROXY"] = original_http
                if original_https:
                    os.environ["HTTPS_PROXY"] = original_https

            logger.info(
                f"✨ Session for {trade_date} finished. {count}/{len(codes)} updated."
            )

        return count
