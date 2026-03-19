"""
db/fund.py — 基金域
====================
基金自选单、持仓、估值、统计、元数据、对账、归因、关系映射。
"""
from datetime import datetime
from psycopg2.extras import Json, DictCursor
from src.lucidpanda.core.logger import logger
from src.lucidpanda.utils import format_iso8601
from src.lucidpanda.db.base import DBBase


class FundRepo(DBBase):

    # ── 自选单 ────────────────────────────────────────────────────────────

    def add_to_watchlist(self, fund_code, fund_name, user_id):
        """Add a fund to the user's watchlist."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO fund_watchlist (user_id, fund_code, fund_name)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (user_id, fund_code) DO UPDATE SET
                            fund_name = EXCLUDED.fund_name,
                            created_at = CURRENT_TIMESTAMP
                    """, (user_id, fund_code, fund_name))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Add to Watchlist Failed: {e}")
            return False

    def remove_from_watchlist(self, fund_code, user_id):
        """Remove a fund from the watchlist."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "DELETE FROM fund_watchlist WHERE user_id = %s AND fund_code = %s",
                        (user_id, fund_code)
                    )
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Remove from Watchlist Failed: {e}")
            return False

    def get_watchlist(self, user_id):
        """Get all funds in the user's watchlist."""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("""
                        SELECT fund_code, fund_name, created_at
                        FROM fund_watchlist
                        WHERE user_id = %s
                        ORDER BY created_at DESC
                    """, (user_id,))
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Watchlist Failed: {e}")
            return []

    def get_watchlist_all_codes(self):
        """Internal helper to get all unique codes across all users."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT DISTINCT fund_code FROM fund_watchlist")
                    codes = [row[0] for row in cursor.fetchall()]
            return codes
        except Exception as e:
            logger.error(f"Get Watchlist All Codes Failed: {e}")
            return []

    # ── 持仓 ──────────────────────────────────────────────────────────────

    def save_fund_holdings(self, fund_code, holdings):
        """Save fund holdings to DB."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM fund_holdings WHERE fund_code = %s", (fund_code,))
                    for h in holdings:
                        cursor.execute("""
                            INSERT INTO fund_holdings (fund_code, stock_code, stock_name, weight, report_date)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (fund_code, h['code'], h['name'], h.get('weight', 0), h.get('report_date', '')))
                    conn.commit()
                    logger.info(f"💾 Saved {len(holdings)} holdings for {fund_code}")
        except Exception as e:
            logger.error(f"Save Fund Holdings Failed: {e}")

    def get_fund_holdings(self, fund_code):
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("SELECT * FROM fund_holdings WHERE fund_code = %s", (fund_code,))
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Fund Holdings Failed: {e}")
            return []

    # ── 估值 ──────────────────────────────────────────────────────────────

    def save_fund_valuation(self, fund_code, growth, details):
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO fund_valuation (fund_code, estimated_growth, details)
                        VALUES (%s, %s, %s)
                    """, (fund_code, growth, Json(details)))
                    conn.commit()
        except Exception as e:
            logger.error(f"Save Fund Valuation Failed: {e}")

    def get_latest_valuation(self, fund_code):
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("""
                        SELECT * FROM fund_valuation
                        WHERE fund_code = %s
                        ORDER BY timestamp DESC LIMIT 1
                    """, (fund_code,))
                    row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get Latest Valuation Failed: {e}")
            return None

    def save_valuation_snapshot(self, trade_date, fund_code, est_growth, components_json, sector_json=None):
        """Save the 15:00 frozen snapshot of a fund valuation."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO fund_valuation_archive
                            (trade_date, fund_code, frozen_est_growth, frozen_components, frozen_sector_attribution)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (trade_date, fund_code) DO UPDATE SET
                            frozen_est_growth = EXCLUDED.frozen_est_growth,
                            frozen_components = EXCLUDED.frozen_components,
                            frozen_sector_attribution = EXCLUDED.frozen_sector_attribution
                    """, (trade_date, fund_code, est_growth, Json(components_json),
                          Json(sector_json) if sector_json else None))
                    conn.commit()
        except Exception as e:
            logger.error(f"Save Valuation Snapshot Failed: {e}")

    def update_official_nav(self, trade_date, fund_code, official_growth):
        """Reconcile official growth, calculate deviations and status."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE fund_valuation_archive
                        SET official_growth = %s
                        WHERE trade_date = %s AND fund_code = %s
                        RETURNING frozen_est_growth
                    """, (official_growth, trade_date, fund_code))
                    row = cursor.fetchone()
                    if row and row[0] is not None:
                        est = float(row[0])
                        off = float(official_growth)
                        dev = est - off
                        abs_dev = abs(dev)
                        status = 'S'
                        if abs_dev >= 1.0:   status = 'C'
                        elif abs_dev >= 0.5: status = 'B'
                        elif abs_dev >= 0.2: status = 'A'
                        cursor.execute("""
                            UPDATE fund_valuation_archive
                            SET deviation = %s, abs_deviation = %s, tracking_status = %s
                            WHERE trade_date = %s AND fund_code = %s
                        """, (dev, abs_dev, status, trade_date, fund_code))
                    conn.commit()
        except Exception as e:
            logger.error(f"Update Official NAV Failed: {e}")

    def get_valuation_history(self, fund_code, limit=30):
        """Fetch historical valuation performance for UI charts."""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("""
                        SELECT trade_date, frozen_est_growth, official_growth, deviation, tracking_status,
                               frozen_sector_attribution AS sector_attribution
                        FROM fund_valuation_archive
                        WHERE fund_code = %s AND official_growth IS NOT NULL
                        ORDER BY trade_date DESC LIMIT %s
                    """, (fund_code, limit))
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Valuation History Failed: {e}")
            return []

    def get_recent_bias(self, fund_code, days=7):
        """Calculate average deviation for dynamic calibration offset."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT AVG(deviation) FROM fund_valuation_archive
                        WHERE fund_code = %s AND official_growth IS NOT NULL
                        AND trade_date > CURRENT_DATE - INTERVAL '%s days'
                    """, (fund_code, days))
                    res = cursor.fetchone()
            return float(res[0]) if res and res[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Get Recent Bias Failed for {fund_code}: {e}")
            return 0.0

    # ── 统计 & 对账 ───────────────────────────────────────────────────────

    def save_fund_stats(self, fund_code, stats):
        """Save calculated fund statistics and grades."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO fund_stats_snapshot (
                            fund_code, return_1w, return_1m, return_3m, return_1y,
                            sharpe_ratio, sharpe_grade, max_drawdown, drawdown_grade,
                            volatility, latest_nav, sparkline_data, last_updated
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, CURRENT_TIMESTAMP)
                        ON CONFLICT (fund_code) DO UPDATE SET
                            return_1w = EXCLUDED.return_1w,
                            return_1m = EXCLUDED.return_1m,
                            return_3m = EXCLUDED.return_3m,
                            return_1y = EXCLUDED.return_1y,
                            sharpe_ratio = EXCLUDED.sharpe_ratio,
                            sharpe_grade = EXCLUDED.sharpe_grade,
                            max_drawdown = EXCLUDED.max_drawdown,
                            drawdown_grade = EXCLUDED.drawdown_grade,
                            volatility = EXCLUDED.volatility,
                            latest_nav = EXCLUDED.latest_nav,
                            sparkline_data = EXCLUDED.sparkline_data,
                            last_updated = CURRENT_TIMESTAMP
                    """, (
                        fund_code,
                        stats.get('return_1w'), stats.get('return_1m'), stats.get('return_3m'), stats.get('return_1y'),
                        stats.get('sharpe'), stats.get('sharpe_grade'),
                        stats.get('max_dd'), stats.get('drawdown_grade'),
                        stats.get('volatility'), stats.get('latest_nav'), Json(stats.get('sparkline')),
                    ))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save Fund Stats Failed for {fund_code}: {e}")
            return False

    def get_fund_stats(self, fund_codes):
        """Batch fetch fund statistics."""
        if not fund_codes: return {}
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("SELECT * FROM fund_stats_snapshot WHERE fund_code = ANY(%s)", (fund_codes,))
                    rows = cursor.fetchall()
            return {r['fund_code']: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"Get Fund Stats Failed: {e}")
            return {}

    def get_reconciliation_stats(self, days=14):
        """Fetch aggregate stats for the monitoring dashboard."""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT trade_date, COUNT(*) as total_count,
                           COUNT(official_growth) as reconciled_count,
                           AVG(ABS(deviation)) as avg_mae
                    FROM fund_valuation_archive
                    WHERE trade_date > CURRENT_DATE - INTERVAL '%s days'
                    GROUP BY trade_date ORDER BY trade_date DESC
                """, (days,))
                daily_stats = [dict(row) for row in cursor.fetchall()]
                cursor.execute("""
                    SELECT fund_code, trade_date, frozen_est_growth, official_growth,
                           deviation, tracking_status
                    FROM fund_valuation_archive
                    WHERE ABS(deviation) >= 1.0
                    AND trade_date > CURRENT_DATE - INTERVAL '7 days'
                    ORDER BY trade_date DESC, ABS(deviation) DESC LIMIT 20
                """)
                anomalies = [dict(row) for row in cursor.fetchall()]
                return {"daily": daily_stats, "anomalies": anomalies,
                        "updated_at": format_iso8601(datetime.now())}
        except Exception as e:
            logger.error(f"Failed to fetch reconciliation stats: {e}")
            return {"daily": [], "anomalies": [], "error": str(e)}
        finally:
            conn.close()

    def get_heatmap_stats(self, days=10):
        """Fetch MAE grouped by category and date for heatmap visualization."""
        try:
            conn = self.get_connection()
            with conn.cursor(cursor_factory=DictCursor) as cursor:
                cursor.execute("""
                    SELECT m.investment_type as category, a.trade_date,
                           AVG(ABS(a.deviation)) as mae, COUNT(*) as sample_count
                    FROM fund_valuation_archive a
                    JOIN fund_metadata m ON a.fund_code = m.fund_code
                    WHERE a.trade_date > CURRENT_DATE - INTERVAL '%s days'
                    AND a.official_growth IS NOT NULL
                    GROUP BY 1, 2 ORDER BY a.trade_date DESC, mae DESC
                """, (days,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Heatmap stats failed: {e}")
            return []
        finally:
            conn.close()

    def delete_valuation_records_by_dates(self, dates: list):
        """Physically remove records for specific dates that have no official growth data."""
        if not dates: return 0
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM fund_valuation_archive
                    WHERE official_growth IS NULL AND trade_date = ANY(%s)
                """, (dates,))
                count = cursor.rowcount
                conn.commit()
                return count
        except Exception as e:
            logger.error(f"Failed to delete records for dates {dates}: {e}")
            return 0
        finally:
            conn.close()

    # ── 元数据 ────────────────────────────────────────────────────────────

    def get_fund_metadata_batch(self, fund_codes: list):
        """Fetch multiple fund metadata (name, type, fee rates) in one query."""
        if not fund_codes: return {}
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT m.fund_code, m.fund_name, m.investment_type,
                           s.mgmt_fee_rate, s.custodian_fee_rate, s.sales_fee_rate
                    FROM fund_metadata m
                    LEFT JOIN fund_stats_snapshot s ON s.fund_code = m.fund_code
                    WHERE m.fund_code = ANY(%s)
                """, (fund_codes,))
                rows = cursor.fetchall()
                return {r[0]: {'name': r[1], 'type': r[2], 'mgmt_fee_rate': r[3],
                                'custodian_fee_rate': r[4], 'sales_fee_rate': r[5]} for r in rows}
        finally:
            conn.close()

    def get_fund_names(self, fund_codes: list):
        """Fetch multiple fund names from metadata in one query."""
        if not fund_codes: return {}
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT fund_code, fund_name FROM fund_metadata WHERE fund_code = ANY(%s)",
                    (fund_codes,)
                )
                return {r[0]: r[1] for r in cursor.fetchall()}
        finally:
            conn.close()

    def search_funds_metadata(self, query, limit=20):
        """Search funds and stocks in local metadata tables (Cross-Asset Pinyin Fuzzy Search).
        
        Priority layers:
          1 - Exact code prefix match
          2 - Pinyin shorthand (first-letter abbreviation) prefix match
          3 - Pinyin full (complete pinyin) prefix match
          4 - Chinese name contains match
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
            
                    query_upper = query.upper()
                    query_lower = query.lower()
            
                    cursor.execute("""
                        (
                            SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type,
                                   c.name as company, 1 as priority
                            FROM fund_metadata m
                            LEFT JOIN fund_companies c ON m.company_id = c.company_id
                            WHERE m.fund_code LIKE %s
                    
                            UNION ALL
                    
                            SELECT s.stock_code as code, s.stock_name as name, s.market as type,
                                   s.industry_l1_name as company, 1 as priority
                            FROM stock_metadata s
                            WHERE s.stock_code LIKE %s
                        )
                        UNION ALL
                        (
                            SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type,
                                   c.name as company, 2 as priority
                            FROM fund_metadata m
                            LEFT JOIN fund_companies c ON m.company_id = c.company_id
                            WHERE m.pinyin_shorthand LIKE %s AND m.fund_code NOT LIKE %s
                    
                            UNION ALL
                    
                            SELECT s.stock_code as code, s.stock_name as name, s.market as type,
                                   s.industry_l1_name as company, 2 as priority
                            FROM stock_metadata s
                            WHERE s.pinyin_shorthand LIKE %s AND s.stock_code NOT LIKE %s
                        )
                        UNION ALL
                        (
                            SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type,
                                   c.name as company, 3 as priority
                            FROM fund_metadata m
                            LEFT JOIN fund_companies c ON m.company_id = c.company_id
                            WHERE m.pinyin_full LIKE %s
                            AND m.fund_code NOT LIKE %s AND m.pinyin_shorthand NOT LIKE %s
                    
                            UNION ALL
                    
                            SELECT s.stock_code as code, s.stock_name as name, s.market as type,
                                   s.industry_l1_name as company, 3 as priority
                            FROM stock_metadata s
                            WHERE s.pinyin_full LIKE %s
                            AND s.stock_code NOT LIKE %s AND (s.pinyin_shorthand IS NULL OR s.pinyin_shorthand NOT LIKE %s)
                        )
                        UNION ALL
                        (
                            SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type,
                                   c.name as company, 4 as priority
                            FROM fund_metadata m
                            LEFT JOIN fund_companies c ON m.company_id = c.company_id
                            WHERE m.fund_name LIKE %s
                            AND m.fund_code NOT LIKE %s AND m.pinyin_shorthand NOT LIKE %s
                            AND (m.pinyin_full IS NULL OR m.pinyin_full NOT LIKE %s)
                    
                            UNION ALL
                    
                            SELECT s.stock_code as code, s.stock_name as name, s.market as type,
                                   s.industry_l1_name as company, 4 as priority
                            FROM stock_metadata s
                            WHERE s.stock_name LIKE %s
                            AND s.stock_code NOT LIKE %s AND (s.pinyin_shorthand IS NULL OR s.pinyin_shorthand NOT LIKE %s)
                            AND (s.pinyin_full IS NULL OR s.pinyin_full NOT LIKE %s)
                        )
                        ORDER BY priority ASC, code ASC LIMIT %s
                    """, (
                        # Priority 1: code prefix
                        f"{query}%", f"{query}%",
                        # Priority 2: pinyin shorthand prefix
                        f"{query_upper}%", f"{query}%", f"{query_upper}%", f"{query}%",
                        # Priority 3: pinyin full contains
                        f"%%{query_lower}%%", f"{query}%", f"{query_upper}%",
                        f"%%{query_lower}%%", f"{query}%", f"{query_upper}%",
                        # Priority 4: Chinese name contains
                        f"%%{query}%%", f"{query}%", f"{query_upper}%", f"{query_lower}%",
                        f"%%{query}%%", f"{query}%", f"{query_upper}%", f"{query_lower}%",
                        limit
                    ))
            
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Search Funds Metadata Failed: {e}")
            return []

    # ── 追踪 ──────────────────────────────────────────────────────────────

    def get_recent_tracking_statuses(self, fund_code, limit=3):
        """Fetch the last N tracking statuses for rebalance detection."""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT tracking_status, deviation FROM fund_valuation_archive
                    WHERE fund_code = %s AND official_growth IS NOT NULL
                    ORDER BY trade_date DESC LIMIT %s
                """, (fund_code, limit))
                rows = cursor.fetchall()
                return [{'status': r[0], 'deviation': float(r[1])} for r in rows if r[0]]
        except Exception as e:
            logger.error(f"Failed to fetch recent statuses for {fund_code}: {e}")
            return []
        finally:
            conn.close()

    def get_fund_performance_metrics(self, fund_code, days=5):
        """Fetch average absolute deviation and sample count for the last N days."""
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT AVG(abs_deviation), COUNT(*) FROM fund_valuation_archive
                    WHERE fund_code = %s AND official_growth IS NOT NULL
                    AND trade_date > CURRENT_DATE - INTERVAL '%s days'
                """, (fund_code, days))
                res = cursor.fetchone()
                return {
                    'avg_mae': float(res[0]) if res and res[0] is not None else None,
                    'sample_count': int(res[1]) if res else 0,
                }
        except Exception as e:
            logger.error(f"Failed to fetch performance metrics: {e}")
            return {'avg_mae': None, 'sample_count': 0}
        finally:
            conn.close()

    # ── 关系映射 ──────────────────────────────────────────────────────────

    def get_fund_relationship(self, sub_code):
        """Retrieve the parent/shadow mapping for a fund."""
        try:
            with self._get_conn() as conn:
                with conn.cursor(cursor_factory=DictCursor) as cursor:
                    cursor.execute("SELECT * FROM fund_relationships WHERE sub_code = %s", (sub_code,))
                    row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get Fund Relationship Failed: {e}")
            return None

    def save_fund_relationship(self, sub_code, parent_code, rel_type="ETF_FEEDER", ratio=0.95):
        """Save or update a fund relationship mapping."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO fund_relationships (sub_code, parent_code, relation_type, ratio, updated_at)
                        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (sub_code) DO UPDATE SET
                            parent_code = EXCLUDED.parent_code,
                            relation_type = EXCLUDED.relation_type,
                            ratio = EXCLUDED.ratio,
                            updated_at = CURRENT_TIMESTAMP
                    """, (sub_code, parent_code, rel_type, ratio))
                    conn.commit()
            return True
        except Exception as e:
            logger.error(f"Save Fund Relationship Failed: {e}")
            return False
