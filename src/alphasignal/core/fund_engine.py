import os
import threading
import akshare as ak
import pandas as pd
import json
import redis
from datetime import datetime, timedelta
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

class FundEngine:
    def __init__(self, db: IntelligenceDB = None):
        self.db = db if db else IntelligenceDB()
        
        # Init Redis
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        try:
            self.redis = redis.from_url(redis_url, decode_responses=True)
            # Lightweight check (optional)
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}")
            self.redis = None

    def update_fund_holdings(self, fund_code):
        """Fetch latest holdings from Market Provider and save to DB."""
        logger.info(f"🔍 Fetching holdings for fund: {fund_code}")
        
        # Temporary disable proxy for data fetching (some sources often fail with proxies)
        original_http = os.environ.get('HTTP_PROXY')
        original_https = os.environ.get('HTTPS_PROXY')
        os.environ['HTTP_PROXY'] = ''
        os.environ['HTTPS_PROXY'] = ''
        
        try:
            # 1. Try last year first (most common case)
            last_year = str(datetime.now().year - 1)
            try:
                df = ak.fund_portfolio_hold_em(symbol=fund_code, date=last_year)
            except:
                df = pd.DataFrame()
            
            if df.empty:
                current_year = str(datetime.now().year)
                try:
                    df = ak.fund_portfolio_hold_em(symbol=fund_code, date=current_year)
                except:
                    pass
                
            if df.empty:
                logger.warning(f"No holdings found for {fund_code}")
                return []
            
            # 2. Sort by quarter to get truly latest
            all_quarters = df['季度'].unique()
            if len(all_quarters) == 0: return []
            
            latest_quarter = sorted(all_quarters, reverse=True)[0]
            logger.info(f"📅 Latest Report: {latest_quarter}")
            
            latest_df = df[df['季度'] == latest_quarter]
            
            holdings = []
            for _, row in latest_df.iterrows():
                holdings.append({
                    'code': str(row['股票代码']),
                    'name': str(row['股票名称']),
                    'weight': float(row['占净值比例']),
                    'report_date': latest_quarter
                })
                
            # Save to DB
            self.db.save_fund_holdings(fund_code, holdings)
            return holdings
            
        except Exception as e:
            logger.error(f"Update Holdings Failed: {e}")
            return []
        finally:
            # Restore proxy if needed
            if original_http:
                os.environ['HTTP_PROXY'] = original_http
            if original_https:
                os.environ['HTTPS_PROXY'] = original_https

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
        patterns = [r'发起式联接', r'发起联接', r'联接', r'[A-Z]$', r'\(.*?\)', r'（.*?）']
        for p in patterns:
            core_name = re.sub(p, '', core_name)
        core_name = core_name.strip()
        
        if not core_name: return None
        
        logger.info(f"🧩 Feeder Detected: '{fund_name}' -> Core: '{core_name}'")
        
        # 2. Search local DB for this core name in fund_metadata
        try:
            conn = self.db.get_connection()
            with conn.cursor() as cursor:
                # Look for matching ETF names
                # Standard ETFs usually start with 51, 15, 56, 58
                cursor.execute("""
                    SELECT fund_code FROM fund_metadata 
                    WHERE (fund_name = %s OR fund_name LIKE %s)
                    AND (fund_code LIKE '51%%' OR fund_code LIKE '15%%' OR fund_code LIKE '56%%' OR fund_code LIKE '58%%')
                    LIMIT 1
                """, (core_name, f"%{core_name}%"))
                row = cursor.fetchone()
                if row:
                    parent_code = row[0]
                    logger.info(f"🎯 Shadow Found: '{fund_name}' -> Parent ETF: {parent_code}")
                    # Save to relationship table for future use
                    self.db.save_fund_relationship(fund_code, parent_code, "ETF_FEEDER")
                    return parent_code
        except Exception as e:
            logger.error(f"Shadow identification DB error: {e}")
        finally:
            if 'conn' in locals() and conn: conn.close()
            
        return None

    def _get_fund_name(self, fund_code):
        """Fetch Fund Name with Redis Cache and Local DB fallback."""
        if self.redis:
            cached_name = self.redis.get(f"fund:name:{fund_code}")
            if cached_name: return cached_name
            
        fund_name = ""
        try:
            # 1. Try local DB first (Fastest fallback)
            names = self.db.get_fund_names([fund_code])
            if names.get(fund_code):
                fund_name = names[fund_code]
            
            # 2. Only if DB missing, try Public API
            if not fund_name:
                # Force disable proxy for reliability
                if "HTTP_PROXY" in os.environ: del os.environ["HTTP_PROXY"]
                if "HTTPS_PROXY" in os.environ: del os.environ["HTTPS_PROXY"]
                
                info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
                fund_name = info_df[info_df.iloc[:,0] == '基金简称'].iloc[0,1]
            
            if self.redis and fund_name:
                self.redis.setex(f"fund:name:{fund_code}", 86400 * 7, fund_name) # 7 days
                
        except:
            pass
        return fund_name or fund_code

    def _get_industry_map(self, stock_codes: list):
        """
        Fetch industry mapping (L1 & L2) for a list of stocks.
        Strategy: Redis Hash 'stock:industry:full' -> DB -> Cache
        Returns: { '600519': {'l1': '食品饮料', 'l2': '白酒'} }
        """
        if not stock_codes: return {}
        if not self.redis: return {}
        
        # 1. Try Fetch from Redis
        try:
            # Redis stores JSON string: "{'l1':..., 'l2':...}"
            raw_data = self.redis.hmget("stock:industry:full", stock_codes)
            
            result = {}
            missing_codes = []
            
            for code, raw_json in zip(stock_codes, raw_data):
                if raw_json:
                    try:
                        result[code] = json.loads(raw_json)
                    except:
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
                    pipeline = self.redis.pipeline() # Initialize pipeline
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            SELECT stock_code, industry_l1_name, industry_l2_name 
                            FROM stock_metadata 
                            WHERE stock_code = ANY(%s)
                        """, (missing_codes,))
                        rows = cursor.fetchall()
                        
                        db_updates = {}
                        for r in rows:
                            val = {'l1': r[1] or "其他", 'l2': r[2] or "其他"}
                            db_updates[r[0]] = json.dumps(val)
                            result[r[0]] = val
                        
                        # Cache found ones back to Redis
                        if db_updates:
                            pipeline.hset("stock:industry:full", mapping=db_updates)
                            
                        # Mark unknowns
                        unknowns = set(missing_codes) - set(result.keys())
                        if unknowns:
                             unknown_val = {'l1': "其他", 'l2': "其他"}
                             unknown_json = json.dumps(unknown_val)
                             unknown_map = {c: unknown_json for c in unknowns}
                             pipeline.hset("stock:industry:full", mapping=unknown_map)
                             for c in unknowns: result[c] = unknown_val
                    pipeline.execute() # Execute pipeline
                finally:
                    conn.close()
                    
            return result
            
        except Exception as e:
            logger.error(f"Industry map fetch failed: {e}")
            return {}

    def calculate_realtime_valuation(self, fund_code):
        """Calculate live estimated NAV growth based on holdings (Source: Market Data)."""
        # 0. Check Cache (Fund Valuation Result)
        if self.redis:
            cached_val = self.redis.get(f"fund:valuation:{fund_code}")
            if cached_val:
                logger.info(f"⚡️ Using cached valuation for {fund_code}")
                return json.loads(cached_val)
        
        # --- NEW: Shadow Mapping Logic ---
        # 1. Check if this is a feeder fund with a mapped shadow ETF
        fund_name = self._get_fund_name(fund_code)
        relationship = self.db.get_fund_relationship(fund_code)
        
        if not relationship:
            # Try to identify it heuristically
            parent_code = self._identify_shadow_etf(fund_code, fund_name)
            if parent_code:
                relationship = {"parent_code": parent_code, "ratio": 0.95}
        
        if relationship:
            parent_code = relationship['parent_code']
            ratio = relationship.get('ratio', 0.95)
            logger.info(f"🕶️ Using Shadow Mapping for {fund_code}: Parent {parent_code}")
            
            # Fetch parent ETF price (using efficient SecID logic)
            # ETFs are field traded, so we use the same batch quote logic but for one item
            secid = None
            if parent_code.startswith(('5', '9')): secid = f"sh{parent_code}"
            else: secid = f"sz{parent_code}"
            
            try:
                import requests
                url = f"http://qt.gtimg.cn/q={secid}"
                res = requests.get(url, timeout=3)
                content = res.content.decode('gbk', errors='ignore')
                
                if '=' in content:
                    val_part = content.split('=', 1)[1].strip('"')
                    parts = val_part.split('~')
                    if len(parts) > 32:
                        price = float(parts[3])
                        pct = float(parts[32])
                        est_growth = pct * ratio
                        
                        result = {
                            "fund_code": fund_code,
                            "fund_name": fund_name,
                            "status": "active",
                            "estimated_growth": round(est_growth, 4),
                            "total_weight": ratio * 100,
                            "components": [{
                                "code": parent_code,
                                "name": self._get_fund_name(parent_code),
                                "price": price,
                                "change_pct": pct,
                                "impact": est_growth,
                                "weight": ratio * 100
                            }],
                            "sector_attribution": {},
                            "timestamp": datetime.now().isoformat(),
                            "source": f"Shadow Mapping ({parent_code})"
                        }
                        if self.redis:
                            self.redis.setex(f"fund:valuation:{fund_code}", 180, json.dumps(result))
                        return result
            except Exception as e:
                logger.error(f"Shadow price fetch failed: {e}")
        # --- END Shadow Mapping ---

        # Force disable proxy for reliability with Market Data
        old_proxies = {}
        for k in ["HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy", "all_proxy", "ALL_PROXY"]:
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
                    if self.redis: self.redis.setex(sync_key, 300, "1")
                    threading.Thread(target=self.update_fund_holdings, args=(fund_code,), daemon=True).start()
                
                return {
                    "fund_code": fund_code,
                    "fund_name": self._get_fund_name(fund_code),
                    "status": "syncing",
                    "estimated_growth": 0,
                    "total_weight": 0,
                    "components": [],
                    "sector_attribution": {},
                    "message": "Holdings missing. Syncing in background...",
                    "source": "System"
                }
                    
            logger.info(f"📈 Calculating valuation for {fund_code} ({len(holdings)} stocks) using Market Data")

            # 2. Identify Markets (A-Share vs HK)
            need_ashare = False
            need_hk = False
            holding_codes = set()
            
            for h in holdings:
                code = h.get('stock_code') or h.get('code')
                if not code: continue
                holding_codes.add(code)
                if len(code) == 6 or (len(code) == 5 and code.startswith("0") and not code.startswith("00")): 
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
                    if c: return pd.read_json(c)
                
                if market_type == 'a':
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
                    df_a = get_market_snapshot('a')
                    # Normalize columns
                    code_col = next((c for c in df_a.columns if '代码' in c), None)
                    price_col = next((c for c in df_a.columns if '最新价' in c), None)
                    change_col = next((c for c in df_a.columns if '涨跌幅' in c), None)
                    
                    if code_col and price_col and change_col:
                        for _, row in df_a.iterrows():
                            c_code = str(row[code_col])
                            if c_code in holding_codes:
                                try:
                                    quote_map[c_code] = {
                                        'price': float(row[price_col]),
                                        'change_pct': float(row[change_col])
                                    }
                                except: pass
                except Exception as e:
                    logger.error(f"Failed to fetch A-share snapshot: {e}")

            # Fetch HK-Shares
            if need_hk:
                try:
                    df_hk = get_market_snapshot('hk')
                    code_col = next((c for c in df_hk.columns if '代码' in c), None)
                    price_col = next((c for c in df_hk.columns if '最新价' in c), None)
                    change_col = next((c for c in df_hk.columns if '涨跌幅' in c), None)
                    
                    if code_col and price_col and change_col:
                        for _, row in df_hk.iterrows():
                            c_code = str(row[code_col])
                            if c_code in holding_codes:
                                try:
                                    quote_map[c_code] = {
                                        'price': float(row[price_col]),
                                        'change_pct': float(row[change_col])
                                    }
                                except: pass
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
                clean_name = re.sub(r'[A-Za-z]+$', '', fund_name)
                clean_name = clean_name.replace('联接', '').replace('发起式', '').replace('发起', '')
                clean_name = re.sub(r'\(.*?\)', '', clean_name).strip()
                
                # Check directly if we have a mapped ETF in cache or map
                # For now, let's try to map via name search if we don't have it
                # Optimization: In a real system, we'd have a mapping table.
                # Here we do a quick name check against holdings? 
                # Better: Check if any holding IS an ETF code (51/15/56/58 start)
                
                for h in holdings:
                    c = h.get('stock_code') or h.get('code')
                    if c and c.startswith(('51', '15', '56', '58')):
                         # It holds an ETF directly!
                         is_feeder = True
                         target_etf = c
                         logger.info(f"🧩 Feeder Fund detected: {fund_code} holds ETF {target_etf}")
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
                         except: pass

                    if etf_quote:
                        # 100% weight on ETF for estimation
                        est_growth = etf_quote['change_pct']
                        
                        result = {
                            "fund_code": fund_code,
                            "fund_name": fund_name,
                            "estimated_growth": round(est_growth, 4),
                            "total_weight": 95.0, # Assumed heavy weight
                            "components": [{
                                "code": target_etf,
                                "name": "Target ETF",
                                "price": etf_quote['price'],
                                "change_pct": etf_quote['change_pct'],
                                "impact": est_growth,
                                "weight": 95.0
                            }],
                            "sector_attribution": {}, # ETF treated as single unit for now
                            "timestamp": datetime.now().isoformat(),
                            "source": "ETF Feeder Penetration"
                        }
                         # Save and return immediately
                        if self.redis:
                            self.redis.setex(f"fund:valuation:{fund_code}", 180, json.dumps(result))
                        return result
                except Exception as e:
                    logger.error(f"Feeder calc failed: {e}")

            # 4. Calculate Valuation & Sector Attribution
            total_impact = 0.0
            total_weight = 0.0
            components = []
            
            # Init Sector Map
            sector_stats = {} 
            
            # Bulk fetch industry mapping
            holding_codes = [h.get('stock_code') or h.get('code') for h in holdings]
            industry_map = self._get_industry_map(holding_codes)
            
            for h in holdings:
                code = h.get('stock_code') or h.get('code')
                weight = h['weight']
                name = h.get('stock_name') or h.get('name') or code
                
                quote = quote_map.get(code)
                current_impact = 0.0
                
                if quote:
                    price = quote['price']
                    pct = quote['change_pct']
                    impact = pct * (weight / 100.0)
                    current_impact = impact
                    
                    total_impact += impact
                    total_weight += weight
                    
                    components.append({
                        "code": code,
                        "name": name,
                        "price": price,
                        "change_pct": pct,
                        "impact": impact,
                        "weight": weight
                    })
                else:
                    components.append({
                        "code": code,
                        "name": name,
                        "price": 0.0,
                        "change_pct": 0.0,
                        "impact": 0.0,
                        "weight": weight,
                        "note": "No Quote"
                    })
                
                # Sector Aggregation
                ind_info = industry_map.get(code, {'l1': "其他", 'l2': "其他"})
                l1 = ind_info.get('l1') or "其他"
                l2 = ind_info.get('l2') or "其他"
                
                if l1 not in sector_stats:
                    sector_stats[l1] = {"impact": 0.0, "weight": 0.0, "sub": {}}
                
                sector_stats[l1]["impact"] += current_impact
                sector_stats[l1]["weight"] += weight
                
                if l2 not in sector_stats[l1]["sub"]:
                    sector_stats[l1]["sub"][l2] = {"impact": 0.0, "weight": 0.0}
                
                sector_stats[l1]["sub"][l2]["impact"] += current_impact
                sector_stats[l1]["sub"][l2]["weight"] += weight

            # 5. Normalize
            final_est = 0.0
            if total_weight > 0:
                final_est = total_impact * (100 / total_weight)
            
            # Fetch Fund Name
            fund_name = self._get_fund_name(fund_code)

            import pytz
            tz_cn = pytz.timezone('Asia/Shanghai')

            # --- Manual Calibration ---
            BIAS_MAP = {
                "018927": 0.62, "018125": 0.56, "018123": 0.65, "023754": 0.42,
                "015790": -0.71, "011068": -0.48, "025209": -0.65
            }
            calibration_note = ""
            if fund_code in BIAS_MAP:
                bias = BIAS_MAP[fund_code]
                final_est += bias
                calibration_note = f" (Incl. Calibration {bias:+.2f}%)"

            result = {
                "fund_code": fund_code,
                "fund_name": fund_name,
                "estimated_growth": round(final_est, 4),
                "total_weight": total_weight,
                "components": components, 
                "sector_attribution": sector_stats,
                "timestamp": datetime.now(tz_cn).isoformat(),
                "source": "System Engine" + calibration_note
            }
            
            # Save to DB history
            try:
                self.db.save_fund_valuation(fund_code, final_est, result)
            except: pass
            
            # Set Cache (180s)
            if self.redis:
                self.redis.setex(f"fund:valuation:{fund_code}", 180, json.dumps(result))
            
            return result
            
        except Exception as e:
            logger.error(f"Valuation Calc Failed: {e}")
            return {"error": str(e)}
            # Restore proxies
            for k, v in old_proxies.items():
                os.environ[k] = v

    def calculate_batch_valuation(self, fund_codes: list, summary: bool = False):
        """
        Calculate valuations for multiple funds in a single batch request using efficient Market API.
        summary: If True, skip components and sector stats for speed.
        """
        import requests
        
        # 0. Pre-fetch Fund Names in Bulk (Avoid serial DB/API calls)
        fund_name_map = {}
        missing_name_codes = []
        if self.redis:
            cached_names = self.redis.mget([f"fund:name:{c}" for c in fund_codes])
            for code, name in zip(fund_codes, cached_names):
                if name: fund_name_map[code] = name
                else: missing_name_codes.append(code)
        else:
            missing_name_codes = fund_codes
            
        if missing_name_codes:
            db_names = self.db.get_fund_names(missing_name_codes)
            for c, n in db_names.items():
                fund_name_map[c] = n
                if self.redis: self.redis.setex(f"fund:name:{c}", 86400 * 7, n)
        
        # 1. Fetch Holdings for ALL funds
        # Use DB first, then fetch missing
        # To avoid sequential fetching of missing holdings, we just do best effort for now or simple loop
        # Optimizing holding fetch is secondary, usually they are in DB.
        
        all_holdings = {}
        stock_map = {} # code -> market_id needed
        
        # --- NEW: Batch Relationship Check ---
        shadow_map = {} # fund_code -> relationship object
        for f_code in fund_codes:
            rel = self.db.get_fund_relationship(f_code)
            if not rel:
                # Try heuristic sync
                p_code = self._identify_shadow_etf(f_code, fund_name_map.get(f_code))
                if p_code: rel = {"parent_code": p_code, "ratio": 0.95}
            
            if rel:
                shadow_map[f_code] = rel
                # Add parent ETF to stock_map for batch quoting
                p_code = rel['parent_code']
                secid = None
                if p_code.startswith(('5', '9')): secid = f"sh{p_code}"
                else: secid = f"sz{p_code}"
                stock_map[p_code] = secid

        # Collect holdings for NON-shadow funds
        for f_code in fund_codes:
            if f_code in shadow_map: continue
            
            holdings = self.db.get_fund_holdings(f_code)
            if not holdings:
                # Start background update and mark as syncing
                sync_key = f"syncing:holdings:{f_code}"
                is_syncing = self.redis.get(sync_key) if self.redis else False
                
                if not is_syncing:
                    if self.redis: self.redis.setex(sync_key, 300, "1")
                    threading.Thread(target=self.update_fund_holdings, args=(f_code,), daemon=True).start()
                
                all_holdings[f_code] = None # Mark as syncing
                continue
            
            all_holdings[f_code] = holdings
            
            for h in holdings:
                s_code = h.get('stock_code') or h.get('code')
                if not s_code: continue
                
                # Determine SecID for Market API
                # Logic: sh6xxxx, sz0xxxx/3xxxx, bj8xxxx/4xxxx, hk0xxxx, usXXXX
                secid = None
                if len(s_code) == 6:
                    if s_code.startswith('6') or s_code.startswith('9'): secid = f"sh{s_code}"
                    elif s_code.startswith('0') or s_code.startswith('3'): secid = f"sz{s_code}"
                    elif s_code.startswith('8') or s_code.startswith('4'): secid = f"bj{s_code}"
                    else: secid = f"sz{s_code}" # Fallback
                elif len(s_code) == 5:
                    secid = f"hk{s_code}"
                elif s_code.isalpha():
                    secid = f"us{s_code}"
                    
                if secid:
                    stock_map[s_code] = secid

        if not stock_map:
            return [{"fund_code": f, "estimated_growth": 0, "error": "No holdings"} for f in fund_codes]

        # 2. Batch Fetch Quotes (Market Node)
        secids_list = list(set(stock_map.values()))
        chunk_size = 60 # Handle more, but keep safe
        quotes = {} # code -> {price, change_pct}
        
        for i in range(0, len(secids_list), chunk_size):
            chunk = secids_list[i:i+chunk_size]
            url = f"http://qt.gtimg.cn/q={','.join(chunk)}"
            
            try:
                # Market Node doesn't need complex headers
                res = requests.get(url, timeout=3)
                # Response is GBK
                content = res.content.decode('gbk', errors='ignore')
                
                # Parse: v_sh600519="1~Name~Code~Price~LastClose~Open~...~...~PCT~..."
                for line in content.split(';'):
                    line = line.strip()
                    if not line: continue
                    
                    # line: v_sh600519="1~..."
                    if '=' not in line: continue
                    
                    key_part, val_part = line.split('=', 1)
                    # key_part: v_sh600519 -> code is sh600519 (remove v_)
                    
                    val_part = val_part.strip('"')
                    parts = val_part.split('~')
                    
                    if len(parts) > 32:
                        try:
                            t_code = parts[2] # Pure code like 600519
                            
                            price = float(parts[3])
                            # Change Pct is usually index 32
                            pct = float(parts[32])
                            
                            # Handle US stock code names
                            if '.' in t_code and not t_code.replace('.','').isdigit():
                                t_code = t_code.split('.')[0] # NVDA.OQ -> NVDA
                                
                            quotes[t_code] = {'price': price, 'change_pct': pct}
                        except: 
                            pass
            except Exception as e:
                logger.error(f"Batch quote fetch failed: {e}")

        # 3. Calculate Valuations
        results = []
        tz_cn = datetime.now().astimezone().replace(tzinfo=None) # simple local time
        
        # Pre-fetch industry mappings (Skip if summary)
        industry_map = {}
        if not summary:
            all_stock_codes = []
            for f_code, holdings in all_holdings.items():
                if holdings:
                    for h in holdings:
                        s_code = h.get('stock_code') or h.get('code')
                        if s_code: all_stock_codes.append(s_code)
            industry_map = self._get_industry_map(list(set(all_stock_codes)))

        for f_code in fund_codes:
            # A. Check Shadow Mapping First
            if f_code in shadow_map:
                rel = shadow_map[f_code]
                p_code = rel['parent_code']
                ratio = rel.get('ratio', 0.95)
                q = quotes.get(p_code)
                
                if q:
                    est_growth = q['change_pct'] * ratio
                    res_obj = {
                        "fund_code": f_code,
                        "fund_name": fund_name_map.get(f_code, f_code),
                        "estimated_growth": round(est_growth, 4),
                        "total_weight": ratio * 100,
                        "components": [] if summary else [{
                            "code": p_code, "name": self._get_fund_name(p_code), "price": q['price'], 
                            "change_pct": q['change_pct'], "impact": est_growth, "weight": ratio * 100
                        }],
                        "sector_attribution": {},
                        "timestamp": datetime.now().isoformat(),
                        "source": f"Shadow Batch ({p_code})"
                    }
                    if self.redis:
                        self.redis.setex(f"fund:valuation:{f_code}", 180, json.dumps(res_obj))
                    results.append(res_obj)
                    continue

            # B. Standard Holdings Logic
            holdings = all_holdings.get(f_code)
            
            if holdings is None:
                # This fund is syncing
                results.append({
                    "fund_code": f_code,
                    "fund_name": fund_name_map.get(f_code, f_code),
                    "estimated_growth": 0,
                    "status": "syncing",
                    "total_weight": 0,
                    "components": [],
                    "sector_attribution": {},
                    "message": "Fetching holdings in background...",
                    "source": "System"
                })
                continue

            if not holdings:
                results.append({
                    "fund_code": f_code, 
                    "fund_name": fund_name_map.get(f_code, f_code),
                    "estimated_growth": 0, 
                    "error": "No holdings data available"
                })
                continue
                
            total_impact = 0.0
            total_weight = 0.0
            components = []
            sector_stats = {}
            
            for h in holdings:
                code = h.get('stock_code') or h.get('code')
                name = h.get('stock_name') or h.get('name') or code
                weight = h['weight']
                
                q = quotes.get(code)
                current_impact = 0.0
                if q:
                    price = q['price']
                    pct = q['change_pct']
                    impact = pct * (weight / 100.0)
                    current_impact = impact
                    total_impact += impact
                    total_weight += weight
                    
                    if not summary:
                        components.append({
                            "code": code, "name": name, "price": price, 
                            "change_pct": pct, "impact": impact, "weight": weight
                        })
                else:
                    if not summary:
                        components.append({
                            "code": code, "name": name, "price": 0, 
                            "change_pct": 0, "impact": 0, "weight": weight, "note": "No Quote"
                        })
                
                # Sector Aggregation (Skip if summary)
                if not summary:
                    ind_info = industry_map.get(code, {'l1': "其他", 'l2': "其他"})
                    l1 = ind_info.get('l1') or "其他"
                    l2 = ind_info.get('l2') or "其他"
                    
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
            
            # --- Manual Calibration (2026-02-04) ---
            # Based on 2026-02-03 Verification
            BIAS_MAP = {
                "018927": 0.62,
                "018125": 0.56,
                "018123": 0.65,
                "023754": 0.42,
                "015790": -0.71,
                "011068": -0.48,
                "025209": -0.65,
                # "007114": 2.46 # Extreme miss, maybe add later
            }
            
            calibration_note = ""
            if f_code in BIAS_MAP:
                bias = BIAS_MAP[f_code]
                final_est += bias
                calibration_note = f" (Incl. Calibration {bias:+.2f}%)"
            
            res_obj = {
                "fund_code": f_code,
                "fund_name": fund_name,
                "estimated_growth": round(final_est, 4),
                "total_weight": total_weight,
                "components": components,
                "sector_attribution": sector_stats,
                "timestamp": datetime.now().isoformat(),
                "source": "System Batch" + calibration_note
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
                logger.info(f"🚀 [Local Hit] Found {len(local_results)} funds for query: {q_strip}")
                return local_results
        except Exception as e:
            logger.warning(f"Local search failed: {e}")
            local_results = []

        # 2. Hard Fallback (0 results locally)
        # This only happens for brand-new funds or non-A-share funds not in metadata.

        # 2. Fallback to API for missing or niche funds
        # Check cache first (24 hour TTL for fund list)
        cache_key = f"fund:search:{query.lower()}"
        if self.redis:
            try:
                cached = self.redis.get(cache_key)
                if cached:
                    logger.info(f"[Cache Hit] Fund search API: {query}")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        try:
            logger.info(f"🔍 Falling back to Market search: {query}")
            
            # Disable proxy for data fetching
            original_http = os.environ.get('HTTP_PROXY')
            original_https = os.environ.get('HTTPS_PROXY')
            os.environ['HTTP_PROXY'] = ''
            os.environ['HTTPS_PROXY'] = ''
            
            try:
                # Get all open-end funds from remote source
                df = ak.fund_name_em()
                
                # Restore proxy
                if original_http:
                    os.environ['HTTP_PROXY'] = original_http
                if original_https:
                    os.environ['HTTPS_PROXY'] = original_https
                
                if df.empty:
                    logger.warning("Remote source returned empty dataframe")
                    return local_results # Return whatever we found locally
                
                # Detect column names (data source may use different names)
                code_col = None
                name_col = None
                type_col = None
                company_col = None
                
                for col in df.columns:
                    col_lower = col.lower()
                    if '代码' in col or 'code' in col_lower:
                        code_col = col
                    elif '名称' in col or '简称' in col or 'name' in col_lower:
                        name_col = col
                    elif '类型' in col or 'type' in col_lower:
                        type_col = col
                    elif '管理人' in col or '公司' in col or 'company' in col_lower:
                        company_col = col
                
                if not code_col or not name_col:
                    logger.error(f"Cannot find code/name columns in remote response")
                    return local_results
                
                # Filter by query (code or name)
                q = query.lower()
                mask = (
                    df[code_col].astype(str).str.contains(q, case=False, na=False) |
                    df[name_col].astype(str).str.contains(q, case=False, na=False)
                )
                filtered = df[mask].head(limit)
                
                # Format results
                api_results = []
                for _, row in filtered.iterrows():
                    api_results.append({
                        'code': str(row[code_col]),
                        'name': str(row[name_col]),
                        'type': str(row[type_col]) if type_col and type_col in row else '混合型',
                        'company': str(row[company_col]) if company_col and company_col in row else ''
                    })
                
                # Merge local and API results, removing duplicates
                seen_codes = {r['code'] for r in local_results}
                merged_results = list(local_results)
                for r in api_results:
                    if r['code'] not in seen_codes:
                        merged_results.append(r)
                
                results = merged_results[:limit]
                logger.info(f"Found {len(results)} results (merged) for query: {query}")
                
                # Cache results
                if self.redis and results:
                    try:
                        self.redis.setex(cache_key, 86400, json.dumps(results))
                    except Exception as e:
                        logger.warning(f"Redis cache write failed: {e}")
                
                return results
                
            except Exception as e:
                # Restore proxy on error
                if original_http:
                    os.environ['HTTP_PROXY'] = original_http
                if original_https:
                    os.environ['HTTPS_PROXY'] = original_https
                logger.error(f"Market search failed: {e}")
                return local_results
                
        except Exception as e:
            logger.error(f"Fund search fallback failed: {e}")
            return local_results

    def take_all_funds_snapshot(self):
        """Batch take snapshots for all funds in various users' watchlists."""
        codes = self.db.get_watchlist_all_codes()
        if not codes:
            logger.info("No funds in watchlist to snapshot.")
            return
        
        logger.info(f"📸 Starting 15:00 Valuation Snapshot for {len(codes)} funds...")
        
        # We can use batch valuation for speed
        valuations = self.calculate_batch_valuation(codes)
        
        trade_date = datetime.now().date()
        
        count = 0
        for val in valuations:
            if 'error' in val: continue
            
            self.db.save_valuation_snapshot(
                trade_date=trade_date,
                fund_code=val['fund_code'],
                est_growth=val['estimated_growth'],
                components_json=val['components'],
                sector_json=val.get('sector_attribution')
            )
            count += 1
            
        logger.info(f"✅ Successfully archived {count} snapshots for {trade_date}")

    def reconcile_official_valuations(self, trade_date=None):
        """
        Fetch real growth for specific funds in the archive by looking up 
        their historical NAV series. Targeted and precise.
        """
        if trade_date is None:
            # Default to the most recent archive date that hasn't been reconciled
            trade_date = datetime.now().date()
            
        # 1. Get the list of funds that need reconciliation for this date
        conn = self.db.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT fund_code FROM fund_valuation_archive 
                    WHERE trade_date = %s AND official_growth IS NULL
                """, (trade_date,))
                codes = [row[0] for row in cursor.fetchall()]
        finally:
            conn.close()
            
        if not codes:
            logger.info(f"No pending reconciliation found for {trade_date}")
            return

        logger.info(f"⚖️ Starting Targeted Reconciliation for {len(codes)} funds on {trade_date}...")
        
        count = 0
        for code in codes:
            try:
                # 2. Fetch the historical NAV series for this specific fund
                # This is more robust than a daily dump as it allows historical backfilling
                df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
                
                if df.empty:
                    logger.warning(f"No NAV history found for {code}")
                    continue
                
                # df usually has columns: ['净值日期', '单位净值', '日增长率', ...]
                # Convert '净值日期' to date objects for comparison
                df['净值日期'] = pd.to_datetime(df['净值日期']).dt.date
                
                # 3. Find the record matching our trade_date
                match = df[df['净值日期'] == trade_date]
                
                if not match.empty:
                    # '日增长率' is usually a string like "1.23" or "0.00"
                    official_growth = float(match.iloc[0]['日增长率'])
                    
                    # 4. Update the archive with the official value and trigger grading
                    self.db.update_official_nav(trade_date, code, official_growth)
                    count += 1
                    logger.info(f"🎯 Matched {code}: Est vs Official applied.")
                else:
                    logger.info(f"⏳ NAV for {code} on {trade_date} not yet released by fund company.")
                    
            except Exception as e:
                logger.error(f"Failed to reconcile {code}: {e}")
            
        logger.info(f"✨ Reconciliation session finished. {count}/{len(codes)} funds updated.")
