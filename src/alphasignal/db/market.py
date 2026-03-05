"""
db/market.py — 市场数据域
==========================
市场快照、交易时段、技术指标、外汇汇率。
"""
from datetime import datetime
import pytz
import akshare as ak
from psycopg2.extras import DictCursor
from src.alphasignal.core.logger import logger
from src.alphasignal.db.base import DBBase


class MarketRepo(DBBase):

    def get_market_session(self, dt=None) -> str:
        """
        Determine market session from UTC timestamp.
        ASIA: 00-08, LONDON: 08-15, NEWYORK: 15-22, LATE_NY: 22-24
        """
        if not dt:
            dt = datetime.now()
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        else:
            dt = dt.astimezone(pytz.utc)
        hour = dt.hour
        if 0 <= hour < 8:   return "ASIA"
        if 8 <= hour < 15:  return "LONDON"
        if 15 <= hour < 22: return "NEWYORK"
        return "LATE_NY"

    def get_advanced_metrics(self, dt, content):
        """
        Calculate Scenario A (Clustering) and Scenario B (Exhaustion).
        Returns (clustering_score: int, exhaustion_score: float)
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM intelligence
                WHERE timestamp BETWEEN %s - INTERVAL '1 hour' AND %s + INTERVAL '1 hour'
            """, (dt, dt))
            clustering_score = cursor.fetchone()[0]

            cursor.execute("""
                SELECT COUNT(*) FROM intelligence
                WHERE timestamp BETWEEN %s - INTERVAL '24 hours' AND %s
                AND urgency_score >= 5
            """, (dt, dt))
            exhaustion_score = float(cursor.fetchone()[0])
            conn.close()
            return clustering_score, exhaustion_score
        except:
            return 0, 0.0

    def get_market_snapshot(self, ticker_symbol, target_time):
        """
        Unified snapshot fetcher for international gold (USD/oz) and macro indices.
        统一使用美元/盎司计价，确保触发价与结果价量级一致。
        """
        try:
            if target_time.tzinfo is None:
                target_time = pytz.utc.localize(target_time)
            else:
                target_time = target_time.astimezone(pytz.utc)

            if ticker_symbol == "GC=F":
                import requests
                try:
                    url = "https://stock.finance.sina.com.cn/futures/api/json_v2.php/GlobalFuturesService.getGlobalFuturesMinLine?symbol=XAU"
                    resp = requests.get(url, timeout=5)
                    data = resp.json()
                    if data and isinstance(data, dict):
                        key = list(data.keys())[0]
                        points = data[key]
                        if points:
                            return round(float(points[-1][1]), 3)
                except Exception as e:
                    logger.warning(f"Sina XAUUSD failed: {e}")
                try:
                    url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=120.XAUUSD&ut=fa5fd1943c0a30548d390f18a2cd7645&fields1=f1&fields2=f53&klt=1&fqt=0&lmt=1"
                    resp = requests.get(url, timeout=5)
                    data = resp.json()
                    if data and "data" in data and data["data"]["klines"]:
                        val = data["data"]["klines"][0].split(",")[1]
                        return round(float(val), 3)
                except Exception as e:
                    logger.warning(f"EastMoney XAUUSD failed: {e}")

            elif ticker_symbol == "DX-Y.NYB":
                try:
                    df = ak.fx_spot_quote()
                    row = df[df['外汇名称'].str.contains('美元指数|USD Index', case=False, na=False)]
                    if not row.empty:
                        return round(float(row.iloc[0]['最新价']), 3)
                except:
                    pass

            elif ticker_symbol == "^TNX":
                try:
                    df = ak.bond_zh_us_rate()
                    if not df.empty:
                        return round(float(df.iloc[-1]['10年']), 3)
                except:
                    pass

            return None
        except Exception as e:
            logger.warning(f"Market Snapshot Failed for {ticker_symbol}: {e}")
            return None

    def get_historical_gold_price(self, target_time=None):
        """Fetch gold price using domestic sources (London Gold spot)."""
        try:
            df = ak.gold_zh_spot_qhkd()
            row = df[df['名称'].str.contains('伦敦金|London Gold', case=False, na=False)]
            if not row.empty:
                return round(float(row.iloc[0]['最新价']), 2)
        except Exception as e:
            logger.warning(f"Gold Price Fetch Failed: {e}")
        return None

    def get_fx_rate_change(self, currency_pair="USD/CNY"):
        """Fetch real-time exchange rate daily change percentage."""
        try:
            df = ak.fx_spot_quote()
            mapping = {
                "USD/CNY": "美元人民币",
                "HKD/CNY": "港元人民币",
                "JPY/CNY": "日元人民币",
                "EUR/CNY": "欧元人民币",
            }
            search_name = mapping.get(currency_pair, currency_pair)
            name_col = next((c for c in df.columns if '名称' in c or '外汇' in c or '货币对' in c), None)
            if not name_col:
                return 0.0
            row = df[df[name_col].str.contains(search_name, case=False, na=False)]
            if not row.empty:
                change_col = next((c for c in row.columns if '涨跌幅' in c or '幅度' in c), None)
                if change_col:
                    return float(row.iloc[0][change_col])
                price_col = next((c for c in row.columns if '最新价' in c), None)
                close_col = next((c for c in row.columns if '昨收' in c or '昨开' in c), None)
                if price_col and close_col:
                    price = float(row.iloc[0][price_col])
                    close = float(row.iloc[0][close_col])
                    if close > 0:
                        return (price - close) / close * 100
            return 0.0
        except Exception as e:
            logger.error(f"Get FX Rate Change Failed for {currency_pair}: {e}")
            return 0.0

    def get_latest_indicator(self, indicator_name, dt=None):
        """Get the most recent indicator value relative to a timestamp."""
        try:
            if not dt:
                dt = datetime.now()
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT * FROM market_indicators
                WHERE indicator_name = %s AND timestamp <= %s
                ORDER BY timestamp DESC LIMIT 1
            """, (indicator_name, dt))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get Indicator Failed: {e}")
            return None

    def save_indicator(self, dt, name, value, percentile=None, description=None):
        """Save or update a market indicator."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_indicators (timestamp, indicator_name, value, percentile, description)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (timestamp, indicator_name) DO UPDATE SET
                    value = EXCLUDED.value,
                    percentile = EXCLUDED.percentile,
                    description = EXCLUDED.description
            """, (dt, name, value, percentile, description))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Save Indicator Failed: {e}")
