"""
db/base.py — 数据库基础设施层
================================
包含：
  - DBConnectionProxy: 连接代理（归还池而非物理断开）
  - DBBase: 基类，持有连接池 + _init_db() 建表 SQL
  - _global_pool / _db_initialized: 全局单例
"""

import json
import logging
from datetime import datetime, timedelta
import pytz
from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except ImportError:
    logger.error("❌ 'psycopg[binary,pool]' is required for PostgreSQL.")
    raise


class DBConnectionProxy:
    """
    代理真实的 psycopg 连接，使 conn.close() 变为归还连接池，
    同时支持 with 语句自动释放，完美解决高并发下的连接耗尽风险。
    """
    def __init__(self, pool):
        self._pool = pool
        self._conn = pool.getconn()

    def __getattr__(self, name):
        if self._conn is None:
            raise RuntimeError("尝试操作已归还连接池的数据库连接")
        return getattr(self._conn, name)

    def close(self):
        if self._pool and self._conn:
            try:
                # 归还连接前，强制 rollback 掉任何未提交的或报错的残留事务
                if getattr(self._conn, 'info', None) and self._conn.info.transaction_status != psycopg.pq.TransactionStatus.IDLE:
                    self._conn.rollback()
            except Exception as e:
                logger.error(f"连接池归还清理异常: {e}")
            self._pool.putconn(self._conn)
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# 全局单例连接池与初始化标志
_global_pool = None
_db_initialized = False


def close_global_pool():
    """显式关闭全局连接池，防止脚本退出时报 FinalizationError"""
    global _global_pool
    if _global_pool:
        try:
            _global_pool.close()
            logger.info("💤 数据库连接池已安全关闭。")
        except Exception as e:
            logger.error(f"❌ 关闭连接池失败: {e}")
        _global_pool = None


class DBBase:
    """
    所有 Repo 子类的基类。
    负责连接池初始化和 Schema 建表。
    """
    def __init__(self):
        """Initialize PostgreSQL Database connection configuration."""
        self.host = settings.POSTGRES_HOST
        self.port = settings.POSTGRES_PORT
        self.user = settings.POSTGRES_USER
        self.password = settings.POSTGRES_PASSWORD
        self.dbname = settings.POSTGRES_DB

        global _global_pool, _db_initialized
        if _global_pool is None:
            try:
                conninfo = f"host={self.host} port={self.port} user={self.user} password={self.password} dbname={self.dbname}"
                _global_pool = ConnectionPool(
                    conninfo=conninfo,
                    min_size=5,
                    max_size=50,
                    timeout=10,
                    kwargs={"row_factory": dict_row}
                )
                logger.info("✅ 数据库连接池已初始化 (min=5, max=50, row_factory=dict_row)")
            except Exception as e:
                logger.error(f"❌ 初始化全局连接池失败: {e}")
                raise

        self._pool = _global_pool

        if not _db_initialized:
            self._init_db()
            _db_initialized = True

    def get_connection(self):
        """
        从连接池获取代理连接。
        conn.close() → 归还连接池，而非物理断开。
        """
        return DBConnectionProxy(self._pool)

    def _get_conn(self):
        return self.get_connection()

    def query(self, sql: str, params: tuple = None) -> list[dict]:
        """执行查询并返回字典列表。"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    return cursor.fetchall()
        except Exception as e:
            logger.error(f"DB Query Failed: {e} | SQL: {sql[:100]}")
            return []

    def execute(self, sql: str, params: tuple = None) -> bool:
        """执行更新/删除/插入并提交。"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params or ())
                    conn.commit()
                    return True
        except Exception as e:
            logger.error(f"DB Execute Failed: {e} | SQL: {sql[:100]}")
            return False

    def _init_db(self):
        """Ensure PostgreSQL schema exists (建表 + Migration)."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()

            try:
                cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
                cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                conn.commit()
            except Exception as e:
                logger.warning(f"⚠️ 安装扩展时失败 (若已手动安装可忽略): {e}")
                conn.rollback()

            # ── intelligence 主表 ─────────────────────────────────────────
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
                    gvz_snapshot DOUBLE PRECISION,
                    oil_price_snapshot DOUBLE PRECISION,
                    corroboration_count INTEGER DEFAULT 1,
                    entities JSONB,
                    relation_triples JSONB,
                    agent_trace JSONB,
                    alpha_return DOUBLE PRECISION,
                    expectation_gap DOUBLE PRECISION,
                    status TEXT DEFAULT 'PENDING',
                    last_error TEXT,
                    category TEXT
                );
            """)

            # Migrations
            for col_sql in [
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_15m DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_1h DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_4h DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_12h DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS price_24h DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS dxy_snapshot DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS us10y_snapshot DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS gvz_snapshot DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS oil_price_snapshot DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS embedding BYTEA;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS embedding_vec vector(768);",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS clustering_score INTEGER DEFAULT 0;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS exhaustion_score DOUBLE PRECISION DEFAULT 0.0;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS market_session TEXT;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS fed_regime DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS macro_adjustment DOUBLE PRECISION DEFAULT 0.0;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS sentiment_score DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS source_name TEXT;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS source_credibility_score DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS agent_trace JSONB;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS alpha_return DOUBLE PRECISION;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS expectation_gap DOUBLE PRECISION;",
                # 事件聚类字段
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS event_cluster_id TEXT;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS corroboration_count INTEGER DEFAULT 1;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS entities JSONB;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS relation_triples JSONB;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS is_cluster_lead BOOLEAN DEFAULT TRUE;",
                # Story Threading 字段：跨轮次追踪同一事件的演进链
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS story_id TEXT;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS is_story_lead BOOLEAN DEFAULT FALSE;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS category TEXT;",
                "ALTER TABLE intelligence ADD COLUMN IF NOT EXISTS tags JSONB;",
            ]:
                cursor.execute(col_sql)
            cursor.execute("UPDATE intelligence SET corroboration_count = 1 WHERE corroboration_count IS NULL;")

            cursor.execute("CREATE INDEX IF NOT EXISTS idx_intel_status ON intelligence(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_intel_event_cluster ON intelligence(event_cluster_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_intel_story_id ON intelligence(story_id);")
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intel_embedding_hnsw
                ON intelligence USING hnsw (embedding_vec vector_cosine_ops)
                WITH (m = 16, ef_construction = 128);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intel_pending_outcomes
                ON intelligence(timestamp DESC)
                WHERE price_1h IS NULL OR price_15m IS NULL OR price_4h IS NULL;
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_intelligence_timestamp ON intelligence(timestamp DESC);
                CREATE INDEX IF NOT EXISTS idx_intelligence_source_id ON intelligence(source_id);
            """)

            # ── 事件知识图谱：节点 / 边 ───────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_nodes (
                    node_id SERIAL PRIMARY KEY,
                    entity_name TEXT NOT NULL,
                    normalized_name TEXT NOT NULL,
                    entity_type TEXT NOT NULL DEFAULT 'unknown',
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(normalized_name, entity_type)
                );
                CREATE INDEX IF NOT EXISTS idx_entity_nodes_norm ON entity_nodes(normalized_name);
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_edges (
                    edge_id SERIAL PRIMARY KEY,
                    from_node_id INTEGER NOT NULL REFERENCES entity_nodes(node_id) ON DELETE CASCADE,
                    to_node_id INTEGER NOT NULL REFERENCES entity_nodes(node_id) ON DELETE CASCADE,
                    relation TEXT NOT NULL,
                    direction TEXT NOT NULL DEFAULT 'forward',
                    strength DOUBLE PRECISION DEFAULT 0.5,
                    confidence_score DOUBLE PRECISION DEFAULT 50.0,
                    event_cluster_id TEXT,
                    evidence_source_id TEXT,
                    intelligence_id INTEGER REFERENCES intelligence(id) ON DELETE SET NULL,
                    metadata JSONB,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(from_node_id, to_node_id, relation, event_cluster_id, evidence_source_id)
                );
                CREATE INDEX IF NOT EXISTS idx_entity_edges_cluster ON entity_edges(event_cluster_id);
                CREATE INDEX IF NOT EXISTS idx_entity_edges_from ON entity_edges(from_node_id);
                CREATE INDEX IF NOT EXISTS idx_entity_edges_to ON entity_edges(to_node_id);
                CREATE INDEX IF NOT EXISTS idx_entity_edges_relation ON entity_edges(relation);
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS relation_rule_stats (
                    relation TEXT PRIMARY KEY,
                    bullish_hits INTEGER DEFAULT 0,
                    bullish_total INTEGER DEFAULT 0,
                    bearish_hits INTEGER DEFAULT 0,
                    bearish_total INTEGER DEFAULT 0,
                    hit_rate DOUBLE PRECISION DEFAULT 0.5,
                    weight DOUBLE PRECISION DEFAULT 1.0,
                    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_relation_rule_weight ON relation_rule_stats(weight DESC);
            """)

            # ── 用户与认证 (PostgreSQL Only) ───────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    email VARCHAR(255) UNIQUE NOT NULL,
                    username VARCHAR(50) UNIQUE,
                    hashed_password VARCHAR(255) NOT NULL,
                    name VARCHAR(100),
                    nickname VARCHAR(100),
                    avatar_url VARCHAR(255),
                    role VARCHAR(20) DEFAULT 'user',
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    language_preference VARCHAR(10) DEFAULT 'en',
                    timezone VARCHAR(50) DEFAULT 'UTC',
                    theme_preference VARCHAR(20) DEFAULT 'system',
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                
                CREATE TABLE IF NOT EXISTS refresh_tokens (
                    id SERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(255) NOT NULL,
                    device_info JSONB,
                    ip_address INET,
                    user_agent TEXT,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_active_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    revoked_at TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash);

                CREATE TABLE IF NOT EXISTS user_passkeys (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    credential_id VARCHAR(512) UNIQUE NOT NULL,
                    public_key TEXT NOT NULL,
                    sign_count INTEGER NOT NULL DEFAULT 0,
                    name VARCHAR(100),
                    transports JSONB,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_used_at TIMESTAMPTZ
                );
                CREATE INDEX IF NOT EXISTS idx_passkeys_credential_id ON user_passkeys(credential_id);

                CREATE TABLE IF NOT EXISTS email_change_requests (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    old_email VARCHAR(255) NOT NULL,
                    new_email VARCHAR(255) NOT NULL,
                    old_email_token_hash VARCHAR(255) UNIQUE,
                    new_email_token_hash VARCHAR(255) UNIQUE,
                    old_email_verified_at TIMESTAMPTZ,
                    new_email_verified_at TIMESTAMPTZ,
                    expires_at TIMESTAMPTZ NOT NULL,
                    is_completed BOOLEAN DEFAULT FALSE,
                    is_cancelled BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
                    token_hash VARCHAR(255) UNIQUE NOT NULL,
                    expires_at TIMESTAMPTZ NOT NULL,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # ── market_indicators ─────────────────────────────────────────
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

            # ── fund_companies ────────────────────────────────────────────
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

            # ── industry_definitions / stock_metadata ─────────────────────
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
                    pinyin_shorthand VARCHAR(50),
                    pinyin_full VARCHAR(255),
                    industry_l1_code VARCHAR(20),
                    industry_l1_name VARCHAR(50),
                    industry_l2_code VARCHAR(20),
                    industry_l2_name VARCHAR(50),
                    market VARCHAR(10),
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_stock_industry_l1 ON stock_metadata(industry_l1_name);
                CREATE INDEX IF NOT EXISTS idx_stock_industry_l2 ON stock_metadata(industry_l2_name);
                CREATE INDEX IF NOT EXISTS idx_stock_pinyin ON stock_metadata(pinyin_shorthand);
            """)

            # ── fund_metadata ─────────────────────────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fund_metadata (
                    fund_code TEXT PRIMARY KEY,
                    fund_name VARCHAR(255) NOT NULL,
                    full_name VARCHAR(512),
                    pinyin_shorthand VARCHAR(100),
                    pinyin_full VARCHAR(255),
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
                CREATE INDEX IF NOT EXISTS idx_fund_pinyin_full ON fund_metadata (pinyin_full);
            """)

            # ── fund_valuation_archive ────────────────────────────────────
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
            cursor.execute("ALTER TABLE fund_valuation_archive ADD COLUMN IF NOT EXISTS frozen_sector_attribution JSONB;")

            # ── fund_managers ─────────────────────────────────────────────
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

            # ── fund_stats_snapshot ───────────────────────────────────────
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
            for col_sql in [
                "ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS sharpe_grade CHAR(1);",
                "ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS drawdown_grade CHAR(1);",
                "ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS return_3m DOUBLE PRECISION;",
                "ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS latest_nav DOUBLE PRECISION;",
                "ALTER TABLE fund_stats_snapshot ADD COLUMN IF NOT EXISTS sparkline_data JSONB;",
            ]:
                cursor.execute(col_sql)

            # ── fund holding / valuation / watchlist / relationships ──────
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
            
            # ── 实体舆情因子时序表 (Factor Indexing) ───────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_metrics (
                    id SERIAL PRIMARY KEY,
                    canonical_id TEXT NOT NULL,
                    metric_date DATE NOT NULL,
                    avg_sentiment DOUBLE PRECISION DEFAULT 0.0,
                    sentiment_sum DOUBLE PRECISION DEFAULT 0.0,
                    mention_count INTEGER DEFAULT 0,
                    urgency_sum INTEGER DEFAULT 0,
                    last_updated TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(canonical_id, metric_date)
                );
                CREATE INDEX IF NOT EXISTS idx_entity_metrics_id_date ON entity_metrics(canonical_id, metric_date);
            """)

            # ── 实体与标签注册表 (Phase 3: Engineering Decoupling) ──────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_registry (
                    canonical_id VARCHAR(64) PRIMARY KEY,
                    display_name VARCHAR(128) NOT NULL,
                    entity_type VARCHAR(32) NOT NULL,
                    description TEXT,
                    importance_weight DOUBLE PRECISION DEFAULT 1.0,
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_entity_registry_type ON entity_registry(entity_type);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_aliases (
                    id SERIAL PRIMARY KEY,
                    alias VARCHAR(128) NOT NULL,
                    canonical_id VARCHAR(64) REFERENCES entity_registry(canonical_id) ON DELETE CASCADE,
                    match_type VARCHAR(16) DEFAULT 'exact',
                    UNIQUE(alias, canonical_id)
                );
                CREATE INDEX IF NOT EXISTS idx_entity_aliases_alias ON entity_aliases(alias);
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS taxonomy_registry (
                    id SERIAL PRIMARY KEY,
                    dimension VARCHAR(32) NOT NULL,
                    value VARCHAR(64) NOT NULL,
                    parent_id INTEGER REFERENCES taxonomy_registry(id),
                    description TEXT,
                    UNIQUE(dimension, value)
                );
            """)
            
            # ── 实体未命中监控表 (Entity Miss Log) ────────────────────────
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS entity_miss_log (
                    raw_entity_name TEXT PRIMARY KEY,
                    occurrence_count INTEGER DEFAULT 1,
                    last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
                    last_source_id TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_entity_miss_count ON entity_miss_log(occurrence_count DESC);
            """)

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"PostgreSQL Init Failed: {e}")
            raise
