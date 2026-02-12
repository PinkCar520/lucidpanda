import json
import logging
from datetime import datetime, timedelta
import pytz
import akshare as ak
import pandas as pd
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger


try:
    import psycopg2
    from psycopg2.extras import Json, DictCursor
except ImportError:
    logger.error("❌ 'psycopg2-binary' is required for PostgreSQL.")
    raise

class IntelligenceDB:
    def __init__(self):
        """Initialize PostgreSQL Database connection configuration."""
        # Ensure we are configured for Postgres
        self.host = settings.POSTGRES_HOST
        self.port = settings.POSTGRES_PORT
        self.user = settings.POSTGRES_USER
        self.password = settings.POSTGRES_PASSWORD
        self.dbname = settings.POSTGRES_DB
        
        self._init_db()

    def get_connection(self):
        """Get a fresh PostgreSQL connection."""
        return psycopg2.connect(
            host=self.host,
            port=self.port,
            user=self.user,
            password=self.password,
            dbname=self.dbname
        )

    def _get_conn(self):
        return self.get_connection()

    def _init_db(self):
        """Ensure PostgreSQL schema exists."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Ensure pg_trgm extension exists for similarity matching
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            
            # Create Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS intelligence (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    source_id TEXT UNIQUE,
                    author TEXT,
                    content TEXT,
                    
                    summary JSONB,
                    sentiment JSONB,
                    urgency_score INTEGER,
                    market_implication JSONB,
                    actionable_advice JSONB,
                    
                    url TEXT,
                    
                    gold_price_snapshot DOUBLE PRECISION,
                    price_15m DOUBLE PRECISION,
                    price_1h DOUBLE PRECISION,
                    price_4h DOUBLE PRECISION,
                    price_12h DOUBLE PRECISION,
                    price_24h DOUBLE PRECISION,
                    market_session TEXT,
                    clustering_score INTEGER DEFAULT 0,
                    exhaustion_score DOUBLE PRECISION DEFAULT 0.0,
                    dxy_snapshot DOUBLE PRECISION,
                    us10y_snapshot DOUBLE PRECISION,
                    gvz_snapshot DOUBLE PRECISION
                );
            """)
            
            # Migration
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_15m DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_1h DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_4h DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_12h DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_24h DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS dxy_snapshot DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS us10y_snapshot DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS gvz_snapshot DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS embedding BYTEA;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'PENDING';")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS last_error TEXT;")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_intel_status ON intelligence(status);")
            
            # Migration
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS clustering_score INTEGER DEFAULT 0;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS exhaustion_score DOUBLE PRECISION DEFAULT 0.0;")
            
            # Market Indicators Table (Weekly/Daily)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_indicators (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ NOT NULL,
                    indicator_name TEXT NOT NULL,
                    value DOUBLE PRECISION,
                    percentile DOUBLE PRECISION,
                    description TEXT,
                    UNIQUE(timestamp, indicator_name)
                );
            """)
            
            # Migration/Update for existing table (Postgres-safe)
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS market_session TEXT;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS fed_regime DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS macro_adjustment DOUBLE PRECISION DEFAULT 0.0;")
            cursor.execute("ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS sentiment_score DOUBLE PRECISION;")
            
            # Fund Companies Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_companies (
                    company_id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    full_name VARCHAR(255),
                    legal_representative VARCHAR(50),
                    establishment_date DATE,
                    location VARCHAR(255),
                    website VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_company_name ON fund_companies(name);
            """)

            # --- Industry Attribution Tables (Added 2026-02-04) ---
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS industry_definitions (
                    industry_code VARCHAR(20) PRIMARY KEY,
                    industry_name VARCHAR(50) NOT NULL,
                    level INTEGER NOT NULL,
                    parent_code VARCHAR(20)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stock_metadata (
                    stock_code VARCHAR(10) PRIMARY KEY,
                    stock_name VARCHAR(50),
                    industry_l1_code VARCHAR(20),
                    industry_l1_name VARCHAR(50),
                    industry_l2_code VARCHAR(20),
                    industry_l2_name VARCHAR(50),
                    market VARCHAR(10),
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_stock_industry_l1 ON stock_metadata(industry_l1_name);
                CREATE INDEX IF NOT EXISTS idx_stock_industry_l2 ON stock_metadata(industry_l2_name);
            """)

            # Fund Metadata Main Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_metadata (
                    fund_code TEXT PRIMARY KEY,
                    fund_name VARCHAR(255) NOT NULL,
                    full_name VARCHAR(512),
                    pinyin_shorthand VARCHAR(100),
                    investment_type VARCHAR(50),
                    style_tag VARCHAR(50),
                    risk_level CHAR(2),
                    company_id INTEGER REFERENCES fund_companies(company_id),
                    inception_date DATE,
                    listing_status VARCHAR(20) DEFAULT 'L',
                    currency CHAR(3) DEFAULT 'CNY',
                    benchmark_text TEXT,
                    last_full_sync TIMESTAMPTZ,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_fund_code_prefix ON fund_metadata (fund_code text_pattern_ops);
                CREATE INDEX IF NOT EXISTS idx_fund_name_trgm ON fund_metadata USING gin (fund_name gin_trgm_ops);
                CREATE INDEX IF NOT EXISTS idx_fund_pinyin ON fund_metadata (pinyin_shorthand);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_valuation_archive (
                    id SERIAL PRIMARY KEY,
                    trade_date DATE NOT NULL,
                    fund_code TEXT NOT NULL,
                    frozen_est_growth NUMERIC(10, 4),
                    frozen_components JSONB,
                    frozen_sector_attribution JSONB,
                    official_growth NUMERIC(10, 4),
                    deviation NUMERIC(10, 4),
                    abs_deviation NUMERIC(10, 4),
                    tracking_status VARCHAR(10),
                    applied_bias_offset NUMERIC(10, 4) DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(trade_date, fund_code)
                );
                CREATE INDEX IF NOT EXISTS idx_archive_date_code ON fund_valuation_archive (trade_date, fund_code);
            """)

            # Migration for Sector Attribution in Archive
            cursor.execute("ALTER TABLE fund_valuation_archive ADD COLUMN IF NOT EXISTS frozen_sector_attribution JSONB;")

            # Fund Managers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_managers (
                    manager_id SERIAL PRIMARY KEY,
                    name VARCHAR(50) NOT NULL,
                    working_years INTEGER,
                    bio TEXT,
                    education VARCHAR(100),
                    is_active BOOLEAN DEFAULT TRUE
                );
                CREATE TABLE IF NOT EXISTS fund_manager_map (
                    fund_code TEXT REFERENCES fund_metadata(fund_code),
                    manager_id INTEGER REFERENCES fund_managers(manager_id),
                    start_date DATE,
                    end_date DATE,
                    position VARCHAR(20),
                    PRIMARY KEY (fund_code, manager_id, start_date)
                );
            """)

            # Fund Stats Snapshot
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_stats_snapshot (
                    fund_code TEXT PRIMARY KEY REFERENCES fund_metadata(fund_code),
                    total_asset DOUBLE PRECISION,
                    net_asset DOUBLE PRECISION,
                    mgmt_fee_rate DOUBLE PRECISION,
                    custodian_fee_rate DOUBLE PRECISION,
                    sales_fee_rate DOUBLE PRECISION,
                    return_1w DOUBLE PRECISION,
                    return_1m DOUBLE PRECISION,
                    return_1y DOUBLE PRECISION,
                    return_since_inception DOUBLE PRECISION,
                    sharpe_ratio DOUBLE PRECISION,
                    max_drawdown DOUBLE PRECISION,
                    volatility DOUBLE PRECISION,
                    sharpe_grade CHAR(1),
                    drawdown_grade CHAR(1),
                    return_3m DOUBLE PRECISION,
                    latest_nav DOUBLE PRECISION,
                    sparkline_data JSONB,
                    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Migration for Fund Stats
            cursor.execute("ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS sharpe_grade CHAR(1);")
            cursor.execute("ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS drawdown_grade CHAR(1);")
            cursor.execute("ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS return_3m DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS latest_nav DOUBLE PRECISION;")
            cursor.execute("ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS sparkline_data JSONB;")

            # Fund Valuation Tables
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_holdings (
                    fund_code TEXT,
                    stock_code TEXT,
                    stock_name TEXT,
                    weight DOUBLE PRECISION,
                    report_date TEXT,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (fund_code, stock_code)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_valuation (
                    fund_code TEXT,
                    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    estimated_growth DOUBLE PRECISION,
                    details JSONB,
                    PRIMARY KEY (fund_code, timestamp)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_watchlist (
                    user_id TEXT DEFAULT 'default',
                    fund_code TEXT,
                    fund_name TEXT,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, fund_code)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_relationships (
                    sub_code VARCHAR(20) PRIMARY KEY,
                    parent_code VARCHAR(20) NOT NULL,
                    relation_type VARCHAR(20) NOT NULL,
                    ratio DOUBLE PRECISION DEFAULT 0.95,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_fund_rel_parent ON fund_relationships(parent_code);
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intelligence_timestamp ON intelligence(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_intelligence_source_id ON intelligence(source_id);
            """)

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"PostgreSQL Init Failed: {e}")
            # If DB init fails, we probably can't run. Let it raise or stay broken.

    # ... (existing methods) ...

    # --- Watchlist Methods ---

    def add_to_watchlist(self, fund_code, fund_name, user_id):
        """Add a fund to the user's watchlist."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fund_watchlist (user_id, fund_code, fund_name)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, fund_code) DO UPDATE SET
                    fund_name = EXCLUDED.fund_name,
                    created_at = CURRENT_TIMESTAMP
            """, (user_id, fund_code, fund_name))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Add to Watchlist Failed: {e}")
            return False

    def remove_from_watchlist(self, fund_code, user_id):
        """Remove a fund from the watchlist."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM fund_watchlist 
                WHERE user_id = %s AND fund_code = %s
            """, (user_id, fund_code))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Remove from Watchlist Failed: {e}")
            return False

    def get_watchlist(self, user_id):
        """Get all funds in the user's watchlist."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT fund_code, fund_name, created_at 
                FROM fund_watchlist 
                WHERE user_id = %s 
                ORDER BY created_at DESC
            """, (user_id,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Watchlist Failed: {e}")
            return []

    def update_outcome(self, record_id, **kwargs):
        """Update historical outcome data dynamically."""
        if not kwargs:
            return
            
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Construct dynamic UPDATE query
            columns = []
            values = []
            for col, val in kwargs.items():
                if val is not None:
                    columns.append(f"{col} = %s")
                    values.append(val)
            
            if columns:
                query = f"UPDATE intelligence SET {', '.join(columns)} WHERE id = %s"
                values.append(record_id)
                cursor.execute(query, tuple(values))
                conn.commit()
                logger.info(f"✅ Outcome Updated ID: {record_id} | Fields: {list(kwargs.keys())}")
            
            conn.close()
        except Exception as e:
            logger.error(f"Update Outcome Failed: {e}")

    def get_pending_outcomes(self):
        """Get records older than 1 hour that lack any of the outcome prices."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            cursor.execute("""
                SELECT * FROM intelligence 
                WHERE (price_1h IS NULL OR price_15m IS NULL OR price_4h IS NULL OR price_12h IS NULL)
                AND timestamp < NOW() - INTERVAL '1 hour'
                ORDER BY timestamp DESC LIMIT 50
            """)
            
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Pending Outcomes Failed: {e}")
            return []


    def save_raw_intelligence(self, raw_data):
        """Save raw intelligence data immediately usually before analysis."""
        try:
            # 1. Parse time
            news_time = None
            if raw_data.get('timestamp'):
                import dateutil.parser
                try:
                    if isinstance(raw_data['timestamp'], str):
                        news_time = dateutil.parser.parse(raw_data['timestamp'])
                    elif hasattr(raw_data['timestamp'], 'tm_year'):
                        from time import mktime
                        import calendar
                        import pytz
                        timestamp_utc = calendar.timegm(raw_data['timestamp'])
                        news_time = datetime.fromtimestamp(timestamp_utc, tz=pytz.utc)
                except Exception as e:
                    logger.warning(f"Timestamp parsing failed: {e}")
            
            import pytz
            if news_time is None:
                news_time = datetime.now(pytz.utc)
            else:
                if news_time.tzinfo is None:
                    news_time = pytz.utc.localize(news_time)
                else:
                    news_time = news_time.astimezone(pytz.utc)

            # Metrics
            market_session = self.get_market_session(news_time)
            clustering_score, exhaustion_score = self.get_advanced_metrics(news_time, raw_data.get('content'))
            
            # Snapshots
            dxy = raw_data.get('dxy_snapshot')
            if dxy is None: dxy = self.get_market_snapshot("DX-Y.NYB", news_time)
                
            us10y = raw_data.get('us10y_snapshot')
            if us10y is None: us10y = self.get_market_snapshot("^TNX", news_time)
                
            gvz = raw_data.get('gvz_snapshot')
            if gvz is None: gvz = self.get_market_snapshot("^GVZ", news_time)
            
            gold = self.get_market_snapshot("GC=F", news_time)

            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Handle Embedding Serialization
            embedding_binary = None
            if 'embedding' in raw_data and raw_data['embedding'] is not None:
                import pickle
                embedding_binary = psycopg2.Binary(pickle.dumps(raw_data['embedding']))

            cursor.execute("""
                INSERT INTO intelligence (
                    source_id, author, content, url, timestamp, 
                    market_session, clustering_score, exhaustion_score,
                    dxy_snapshot, us10y_snapshot, gvz_snapshot, gold_price_snapshot,
                    fed_regime, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE SET 
                    author = EXCLUDED.author -- Minimal update to trigger RETURNING
                RETURNING id
            """, (
                raw_data.get('id'),
                raw_data.get('author'),
                raw_data.get('original_content') if raw_data.get('original_content') else raw_data.get('content'), 
                raw_data.get('url'),
                news_time,
                market_session,
                clustering_score,
                float(exhaustion_score),
                float(dxy) if dxy is not None else None,
                float(us10y) if us10y is not None else None,
                float(gvz) if gvz is not None else None,
                float(gold) if gold is not None else None,
                float(raw_data.get('fed_val', 0.0)),
                embedding_binary
            ))
            
            row = cursor.fetchone()
            conn.commit()
            conn.close()
            
            return row[0] if row else None
            
        except Exception as e:
            logger.error(f"Save Raw Failed: {e}")
            return None

    def update_intelligence_analysis(self, source_id, analysis_result, raw_data):
        """Update a record with analysis results."""
        try:
            # Re-calc macro (or pass it in?)
            sentiment_score = analysis_result.get('sentiment_score', 0)
            orig_score = sentiment_score
            fed_val = raw_data.get('fed_val', 0)
            
            macro_adj = 0.0
            if fed_val > 0: # Dovish
                macro_adj = 0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score + 0.15))
                logger.info(f"⚖️  Dimension D 权调节 (Dovish/+0.15): {orig_score:.2f} -> {sentiment_score:.2f}")
            elif fed_val < 0: # Hawkish
                macro_adj = -0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score - 0.15))
                logger.info(f"⚖️  Dimension D 权调节 (Hawkish/-0.15): {orig_score:.2f} -> {sentiment_score:.2f}")

            def to_jsonb(val):
                if isinstance(val, (dict, list)): return Json(val)
                return Json(val)

            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Handle Embedding Serialization
            embedding_binary = None
            if 'embedding' in analysis_result and analysis_result['embedding'] is not None:
                import pickle
                embedding_binary = psycopg2.Binary(pickle.dumps(analysis_result['embedding']))

            cursor.execute("""
                UPDATE intelligence SET
                    summary = %s,
                    sentiment = %s,
                    urgency_score = %s,
                    market_implication = %s,
                    actionable_advice = %s,
                    sentiment_score = %s,
                    macro_adjustment = %s,
                    embedding = COALESCE(%s, embedding),
                    status = 'COMPLETED',
                    last_error = NULL
                WHERE source_id = %s
            """, (
                to_jsonb(analysis_result.get('summary')),
                to_jsonb(analysis_result.get('sentiment')),
                analysis_result.get('urgency_score'),
                to_jsonb(analysis_result.get('market_implication')),
                to_jsonb(analysis_result.get('actionable_advice')),
                float(sentiment_score),
                float(macro_adj),
                embedding_binary,
                source_id
            ))
            
            conn.commit()
            conn.close()
            logger.info(f"💾 Updated Analysis for ID: {source_id}")
            
        except Exception as e:
            logger.error(f"Update Analysis Failed: {e}")


    def save_intelligence(self, raw_data, analysis_result, gold_price_snapshot=None, price_1h=None, price_24h=None):
        """
        Save intelligence to PostgreSQL using JSONB.
        
        Args:
            raw_data: Raw news data
            analysis_result: AI analysis result
            gold_price_snapshot: Optional pre-fetched gold price at event time (for historical imports)
            price_1h: Optional gold price 1 hour after event (for historical imports)
            price_24h: Optional gold price 24 hours after event (for historical imports)
            dxy_snapshot: Optional DXY price at event time
            us10y_snapshot: Optional US10Y yield at event time
            gvz_snapshot: Optional GVZ (volatility) at event time
        """
        try:
            # 1. Parse time (to timezone-aware datetime)
            news_time = None
            if raw_data.get('timestamp'):
                import dateutil.parser
                try:
                    if isinstance(raw_data['timestamp'], str):
                        news_time = dateutil.parser.parse(raw_data['timestamp'])
                        logger.info(f"Parsed timestamp from string: {raw_data['timestamp']} -> {news_time}")
                    elif hasattr(raw_data['timestamp'], 'tm_year'):
                        from time import mktime
                        import calendar
                        import pytz
                        # Use calendar.timegm for UTC time.struct_time (not mktime which assumes local time)
                        timestamp_utc = calendar.timegm(raw_data['timestamp'])
                        news_time = datetime.fromtimestamp(timestamp_utc, tz=pytz.utc)
                        logger.info(f"Parsed timestamp from struct_time: {raw_data['timestamp']} -> {news_time}")
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp {raw_data.get('timestamp')}: {e}")
            
            # 1.5 Calculate Market Session
            market_session = self.get_market_session(news_time)
            
            # 1.6 Advanced Trading Metrics (Clustering & Exhaustion)
            clustering_score, exhaustion_score = self.get_advanced_metrics(news_time, raw_data.get('content'))
            
            # 2. Get real-time snapshots if missing (for live processing)
            import pytz
            if news_time is None:
                logger.warning(f"No valid timestamp found for news, using current time. URL: {raw_data.get('url')}")
                news_time = datetime.now(pytz.utc)
            else:
                if news_time.tzinfo is None:
                    news_time = pytz.utc.localize(news_time)
                else:
                    news_time = news_time.astimezone(pytz.utc)

            if gold_price_snapshot is None:
                gold_price_snapshot = self.get_market_snapshot("GC=F", news_time)
            
            dxy = raw_data.get('dxy_snapshot')
            if dxy is None:
                dxy = self.get_market_snapshot("DX-Y.NYB", news_time)
            
            us10y = raw_data.get('us10y_snapshot')
            if us10y is None:
                us10y = self.get_market_snapshot("^TNX", news_time)
                
            gvz = raw_data.get('gvz_snapshot')
            if gvz is None:
                gvz = self.get_market_snapshot("^GVZ", news_time)
            
            sentiment_score = analysis_result.get('sentiment_score', 0)
            orig_score = sentiment_score
            
            fed_val = raw_data.get('fed_val', 0)


            
            # Macro Regime Offset (Dimension D)
            macro_adj = 0.0
            if fed_val > 0: # Dovish
                macro_adj = 0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score + 0.15))
                logger.info(f"⚖️  Dimension D 权调节 (Dovish/+0.15): {orig_score:.2f} -> {sentiment_score:.2f}")
            elif fed_val < 0: # Hawkish
                macro_adj = -0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score - 0.15))
                logger.info(f"⚖️  Dimension D 权调节 (Hawkish/-0.15): {orig_score:.2f} -> {sentiment_score:.2f}")
            
            current_gold_price = gold_price_snapshot
            
            conn = self._get_conn()
            cursor = conn.cursor()

            def to_jsonb(val):
                """Ensure valid JSON or wrap text in JSON structure"""
                if isinstance(val, (dict, list)): return Json(val)
                # If it's pure text, wrap it or store as string if field allows (but we defined JSONB)
                # For i18n fields, if we get a raw string, we might want to wrap it: {"raw": str}
                # But to stay compatible with frontend which expects object, let's wrap.
                return Json(val)

            cursor.execute("""
                INSERT INTO intelligence (
                    source_id, author, content, summary, sentiment, 
                    urgency_score, market_implication, actionable_advice, url,
                    gold_price_snapshot, price_1h, price_24h, timestamp, market_session,
                    clustering_score, exhaustion_score, dxy_snapshot, us10y_snapshot, gvz_snapshot,
                    sentiment_score, fed_regime, macro_adjustment
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO NOTHING
            """, (
                raw_data.get('id'),
                raw_data.get('author'),
                raw_data.get('content'),
                to_jsonb(analysis_result.get('summary')),
                to_jsonb(analysis_result.get('sentiment')),
                analysis_result.get('urgency_score'),
                to_jsonb(analysis_result.get('market_implication')),
                to_jsonb(analysis_result.get('actionable_advice')),
                raw_data.get('url'),
                float(current_gold_price) if current_gold_price is not None else None,
                float(price_1h) if price_1h is not None else None,
                float(price_24h) if price_24h is not None else None,
                news_time,
                market_session,
                clustering_score,
                float(exhaustion_score) if exhaustion_score is not None else 0.0,
                float(dxy) if dxy is not None else None,
                float(us10y) if us10y is not None else None,
                float(gvz) if gvz is not None else None,
                float(sentiment_score),
                float(fed_val) if fed_val is not None else 0.0,
                float(macro_adj)
            ))

            conn.commit()
            if cursor.rowcount > 0:
                price_info = f"${current_gold_price}"
                if price_1h:
                    price_info += f" | 1h: ${price_1h}"
                if price_24h:
                    price_info += f" | 24h: ${price_24h}"
                logger.info(f"💾 Saved Intelligence to Postgres | Gold: {price_info}")
            
            conn.close()

        except Exception as e:
            logger.error(f"Save Intelligence Failed: {e}")

    def get_market_session(self, dt=None):
        """
        Determine market session from timestamp (UTC).
        Asia: 00:00 - 08:00
        London: 08:00 - 15:00
        New York: 15:00 - 22:00
        Gap/Late NY: 22:00 - 24:00
        """
        if not dt:
            dt = datetime.now()
        
        # Ensure UTC
        import pytz
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        else:
            dt = dt.astimezone(pytz.utc)
            
        hour = dt.hour
        
        if 0 <= hour < 8:
            return "ASIA"
        elif 8 <= hour < 15:
            return "LONDON"
        elif 15 <= hour < 22:
            return "NEWYORK"
        else:
            return "LATE_NY"

    def get_advanced_metrics(self, dt, content):
        """
        Calculate Scenario A (Clustering) and Scenario B (Exhaustion)
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Clustering Score (Scenario A): News items in the last 1 hour
            # We look for ANY news items within 1 hour to see if signal is "mixed"
            cursor.execute("""
                SELECT COUNT(*) FROM intelligence 
                WHERE timestamp BETWEEN %s - INTERVAL '1 hour' AND %s + INTERVAL '1 hour'
            """, (dt, dt))
            clustering_score = cursor.fetchone()[0]
            
            # 2. Exhaustion Score (Scenario B): Sentiment slope last 24h
            # Count similar bearish news to see if "market has already sold off"
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
        """Unified snapshot fetcher for domestic-friendly environment"""
        try:
            # Normalize target_time to UTC
            if target_time.tzinfo is None:
                target_time = pytz.utc.localize(target_time)
            else:
                target_time = target_time.astimezone(pytz.utc)
            
            # Map Ticker to Data Source logic
            if ticker_symbol == "GC=F": # International Gold Spot (London Gold)
                try:
                    df = ak.gold_zh_spot_qhkd()
                    row = df[df['名称'].str.contains('伦敦金|London Gold', case=False, na=False)]
                    if not row.empty:
                        return round(float(row.iloc[0]['最新价']), 3)
                except:
                    pass
            
            elif ticker_symbol == "DX-Y.NYB": # DXY (USD Index)
                try:
                    df = ak.fx_spot_quote()
                    row = df[df['外汇名称'].str.contains('美元指数|USD Index', case=False, na=False)]
                    if not row.empty:
                        return round(float(row.iloc[0]['最新价']), 3)
                except:
                    pass
            
            elif ticker_symbol == "^TNX": # US10Y Yield
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
        """Fetch gold price using domestic sources."""
        try:
            # Provide the London Gold spot from domestic sources via Market API
            df = ak.gold_zh_spot_qhkd()
            row = df[df['名称'].str.contains('伦敦金|London Gold', case=False, na=False)]
            if not row.empty:
                return round(float(row.iloc[0]['最新价']), 2)
        except Exception as e:
            logger.warning(f"Gold Price Fetch Failed: {e}")
        return None

    def get_fx_rate_change(self, currency_pair="USD/CNY"):
        """
        Fetch real-time exchange rate daily change percentage.
        Supports USD/CNY, HKD/CNY etc.
        """
        try:
            # Use Sina FX spot quote via AkShare
            df = ak.fx_spot_quote()
            
            mapping = {
                "USD/CNY": "美元人民币",
                "HKD/CNY": "港元人民币",
                "JPY/CNY": "日元人民币",
                "EUR/CNY": "欧元人民币"
            }
            
            search_name = mapping.get(currency_pair, currency_pair)
            
            # Find the name column dynamically
            name_col = next((c for c in df.columns if '名称' in c or '外汇' in c or '货币对' in c), None)
            if not name_col:
                return 0.0
                
            row = df[df[name_col].str.contains(search_name, case=False, na=False)]
            
            if not row.empty:
                # Some versions of AkShare use '涨跌幅', others might use different names
                change_col = next((c for c in row.columns if '涨跌幅' in c or '幅度' in c), None)
                if change_col:
                    return float(row.iloc[0][change_col])
                
                # If no direct percentage, calculate from Last Close if available
                price_col = next((c for c in row.columns if '最新价' in c), None)
                close_col = next((c for c in row.columns if '昨收' in c or '昨开' in c), None) # Fallback heuristic
                
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

    def get_recent_intelligence(self, limit=10):
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT * FROM intelligence ORDER BY timestamp DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Recent Failed: {e}")
            return []

    def get_pending_intelligence(self, limit=20):
        """Fetch records that need AI analysis or retries."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            # Fetch PENDING or FAILED records
            cursor.execute("""
                SELECT * FROM intelligence 
                WHERE status IN ('PENDING', 'FAILED') 
                ORDER BY timestamp DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Pending Failed: {e}")
            return []

    def update_intelligence_status(self, source_id, status, error=None):
        """Update the lifecycle status of an intelligence item."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE intelligence 
                SET status = %s, last_error = %s 
                WHERE source_id = %s
            """, (status, error, source_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Update Status Failed: {e}")

    def check_analysis_exists(self, source_id):
        """Check if a record already has AI analysis data."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM intelligence WHERE source_id = %s AND summary IS NOT NULL LIMIT 1", (source_id,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except:
            return False

    def is_duplicate(self, new_url, new_content, new_summary=None) -> bool:
        """
        Checks for duplicate intelligence using URL and pg_trgm for content similarity.
        
        Args:
            new_url (str): The URL of the new intelligence item.
            new_content (str): The main content of the new intelligence item.
            new_summary (str): The summary of the new intelligence item.
        Returns:
            bool: True if a duplicate is found, False otherwise.
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 1. Exact URL match (most reliable)
            cursor.execute("SELECT id FROM intelligence WHERE url = %s LIMIT 1", (new_url,))
            if cursor.fetchone():
                logger.info(f"🚫 URL {new_url} 已存在，跳过。")
                conn.close()
                return True

            # 2. Semantic similarity check using pg_trgm on content/summary
            # Only check against recent items to avoid performance issues on large datasets
            time_window = datetime.now() - timedelta(hours=settings.NEWS_DEDUPE_WINDOW_HOURS)
            
            # Combine content and summary for a more robust similarity check
            new_text_for_sim = f"{new_content} {new_summary if new_summary else ''}"
            
            # Use COALESCE to handle potentially null content/summary in DB
            cursor.execute("""
                SELECT id, similarity(COALESCE(content, '') || ' ' || COALESCE(summary::text, ''), %s) AS sim_score
                FROM intelligence 
                WHERE timestamp > %s
                AND (
                    similarity(COALESCE(content, ''), %s) > %s OR
                    similarity(COALESCE(summary::text, ''), %s) > %s OR
                    similarity(COALESCE(content, '') || ' ' || COALESCE(summary::text, ''), %s) > %s
                )
                ORDER BY sim_score DESC
                LIMIT 1
            """, (new_text_for_sim, time_window, new_content, settings.NEWS_SIMILARITY_THRESHOLD,
                  new_summary if new_summary else '', settings.NEWS_SIMILARITY_THRESHOLD,
                  new_text_for_sim, settings.NEWS_SIMILARITY_THRESHOLD))
            
            result = cursor.fetchone()
            conn.close()

            if result:
                logger.info(f"🚫 发现语义重复情报 (ID: {result[0]}, 相似度: {result[1]:.2f})，跳过。")
                return True
                
            return False
        except Exception as e:
            logger.error(f"Duplicate Check Failed: {e}")
            # In case of error, assume it's not a duplicate to avoid blocking new intelligence
            return False
            
    # --- Fund Valuation Methods ---

    def get_fund_metadata_batch(self, fund_codes: list):
        """Fetch multiple fund metadata (name, type) in one query."""
        if not fund_codes: return {}
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT fund_code, fund_name, investment_type FROM fund_metadata WHERE fund_code = ANY(%s)", (fund_codes,))
                rows = cursor.fetchall()
                return {r[0]: {'name': r[1], 'type': r[2]} for r in rows}
        finally:
            conn.close()

    def get_fund_names(self, fund_codes: list):
        """Fetch multiple fund names from metadata in one query."""
        if not fund_codes: return {}
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT fund_code, fund_name FROM fund_metadata WHERE fund_code = ANY(%s)", (fund_codes,))
                rows = cursor.fetchall()
                return {r[0]: r[1] for r in rows}
        finally:
            conn.close()

    def save_fund_holdings(self, fund_code, holdings):
        """Save fund holdings to DB."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # First clean old holdings for this fund
            cursor.execute("DELETE FROM fund_holdings WHERE fund_code = %s", (fund_code,))
            
            for h in holdings:
                cursor.execute("""
                    INSERT INTO fund_holdings (fund_code, stock_code, stock_name, weight, report_date)
                    VALUES (%s, %s, %s, %s, %s)
                """, (fund_code, h['code'], h['name'], h.get('weight', 0), h.get('report_date', '')))
                
            conn.commit()
            conn.close()
            logger.info(f"💾 Saved {len(holdings)} holdings for {fund_code}")
        except Exception as e:
            logger.error(f"Save Fund Holdings Failed: {e}")

    def get_fund_holdings(self, fund_code):
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT * FROM fund_holdings WHERE fund_code = %s", (fund_code,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Fund Holdings Failed: {e}")
            return []

    def save_fund_valuation(self, fund_code, growth, details):
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fund_valuation (fund_code, estimated_growth, details)
                VALUES (%s, %s, %s)
            """, (fund_code, growth, Json(details)))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Save Fund Valuation Failed: {e}")

    def get_latest_valuation(self, fund_code):
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT * FROM fund_valuation 
                WHERE fund_code = %s 
                ORDER BY timestamp DESC LIMIT 1
            """, (fund_code,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get Latest Valuation Failed: {e}")
            return None

    def save_fund_stats(self, fund_code, stats):
        """Save calculated fund statistics and grades."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fund_stats_snapshot (
                    fund_code, return_1w, return_1m, return_3m, return_1y,
                    sharpe_ratio, sharpe_grade, max_drawdown, drawdown_grade,
                    volatility, latest_nav, sparkline_data, last_updated
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
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
                stats.get('volatility'), stats.get('latest_nav'), Json(stats.get('sparkline'))
            ))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Save Fund Stats Failed for {fund_code}: {e}")
            return False

    def get_fund_stats(self, fund_codes):
        """Batch fetch fund statistics."""
        if not fund_codes: return {}
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT * FROM fund_stats_snapshot WHERE fund_code = ANY(%s)", (fund_codes,))
            rows = cursor.fetchall()
            conn.close()
            return {r['fund_code']: dict(r) for r in rows}
        except Exception as e:
            logger.error(f"Get Fund Stats Failed: {e}")
            return {}

    def search_funds_metadata(self, query, limit=20):
        """Search funds in local metadata table."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            
            # Using UNION to prioritize exact or prefix matches on code
            # and then name/pinyin matches.
            cursor.execute("""
                (
                    SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type, c.name as company, 1 as priority
                    FROM fund_metadata m
                    LEFT JOIN fund_companies c ON m.company_id = c.company_id
                    WHERE m.fund_code LIKE %s
                )
                UNION ALL
                (
                    SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type, c.name as company, 2 as priority
                    FROM fund_metadata m
                    LEFT JOIN fund_companies c ON m.company_id = c.company_id
                    WHERE m.pinyin_shorthand LIKE %s
                    AND m.fund_code NOT LIKE %s
                )
                UNION ALL
                (
                    SELECT m.fund_code as code, m.fund_name as name, m.investment_type as type, c.name as company, 3 as priority
                    FROM fund_metadata m
                    LEFT JOIN fund_companies c ON m.company_id = c.company_id
                    WHERE m.fund_name LIKE %s
                    AND m.fund_code NOT LIKE %s
                    AND m.pinyin_shorthand NOT LIKE %s
                )
                ORDER BY priority ASC, code ASC
                LIMIT %s
            """, (f"{query}%", f"{query.upper()}%", f"{query}%", f"%%{query}%%", f"{query}%", f"{query.upper()}%", limit))
            
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Search Funds Metadata Failed: {e}")
            return []

    def save_valuation_snapshot(self, trade_date, fund_code, est_growth, components_json, sector_json=None):
        """Save the 15:00 frozen snapshot of a fund valuation."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO fund_valuation_archive (trade_date, fund_code, frozen_est_growth, frozen_components, frozen_sector_attribution)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (trade_date, fund_code) DO UPDATE SET
                    frozen_est_growth = EXCLUDED.frozen_est_growth,
                    frozen_components = EXCLUDED.frozen_components,
                    frozen_sector_attribution = EXCLUDED.frozen_sector_attribution
            """, (trade_date, fund_code, est_growth, Json(components_json), Json(sector_json) if sector_json else None))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Save Valuation Snapshot Failed: {e}")

    def update_official_nav(self, trade_date, fund_code, official_growth):
        """Reconcile official growth, calculate deviations and status."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            # 1. Update growth
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
                
                # Grade the accuracy
                # S: < 0.2%, A: < 0.5%, B: < 1.0%, C: > 1.0%
                status = 'S'
                if abs_dev >= 1.0: status = 'C'
                elif abs_dev >= 0.5: status = 'B'
                elif abs_dev >= 0.2: status = 'A'
                
                cursor.execute("""
                    UPDATE fund_valuation_archive
                    SET deviation = %s, abs_deviation = %s, tracking_status = %s
                    WHERE trade_date = %s AND fund_code = %s
                """, (dev, abs_dev, status, trade_date, fund_code))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Update Official NAV Failed: {e}")

    def get_valuation_history(self, fund_code, limit=30):
        """Fetch historical valuation performance for UI charts."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT trade_date, frozen_est_growth, official_growth, deviation, tracking_status, 
                       frozen_sector_attribution AS sector_attribution
                FROM fund_valuation_archive
                WHERE fund_code = %s AND official_growth IS NOT NULL
                ORDER BY trade_date DESC
                LIMIT %s
            """, (fund_code, limit))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Valuation History Failed: {e}")
            return []

    def get_recent_bias(self, fund_code, days=7):
        """Calculate the average deviation for a fund over the last N days to use as a dynamic calibration offset."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            # We take the average deviation from the last N records where official_growth was reconciled
            cursor.execute("""
                SELECT AVG(deviation) 
                FROM fund_valuation_archive 
                WHERE fund_code = %s 
                AND official_growth IS NOT NULL
                AND trade_date > CURRENT_DATE - INTERVAL '%s days'
            """, (fund_code, days))
            res = cursor.fetchone()
            conn.close()
            
            # Return the bias if exists, otherwise 0
            return float(res[0]) if res and res[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Get Recent Bias Failed for {fund_code}: {e}")
            return 0.0

    def get_watchlist_all_codes(self):
        """Internal helper to get all unique codes across all users for batch snapshots."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT fund_code FROM fund_watchlist")
            codes = [row[0] for row in cursor.fetchall()]
            conn.close()
            return codes
        except Exception as e:
            logger.error(f"Get Watchlist All Codes Failed: {e}")
            return []

    # --- Fund Relationship Methods (Shadow Mapping) ---

    def get_fund_relationship(self, sub_code):
        """Retrieve the parent/shadow mapping for a fund."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT * FROM fund_relationships WHERE sub_code = %s", (sub_code,))
            row = cursor.fetchone()
            conn.close()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"Get Fund Relationship Failed: {e}")
            return None

    def save_fund_relationship(self, sub_code, parent_code, rel_type="ETF_FEEDER", ratio=0.95):
        """Save or update a fund relationship mapping."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
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
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Save Fund Relationship Failed: {e}")
            return False
