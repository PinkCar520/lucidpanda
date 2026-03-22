-- 数据库首次初始化时自动加载两大核心扩展
-- pgvector + TimescaleDB 融合引擎
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS vector;
