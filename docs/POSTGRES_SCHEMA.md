# PostgreSQL Schema Design for LucidPanda

## Overview
This document outlines the database schema for migrating LucidPanda from SQLite to PostgreSQL. The migration aims to support better concurrency, richer data types (JSONB), and scalability.

## Schema Definition

```sql
-- Main Intelligence Table
CREATE TABLE IF NOT EXISTS intelligence (
    -- ID: Auto-incrementing integer (using SERIAL or IDENTITY)
    id SERIAL PRIMARY KEY,
    
    -- Timestamp: Store with timezone for global accuracy
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Source ID: Unique identifier from the data source (prevent duplicates)
    source_id TEXT UNIQUE,
    
    -- Metadata
    author TEXT,
    url TEXT,
    
    -- Raw Content
    content TEXT,
    
    -- AI Analysis (Stored as JSONB for efficient querying and i18n support)
    -- Structure: {"en": "...", "zh": "..."}
    summary JSONB,
    sentiment JSONB,
    market_implication JSONB,
    actionable_advice JSONB,
    
    -- Scores & Metrics
    urgency_score INTEGER,
    
    -- Market Data Snapshots (Gold Price)
    gold_price_snapshot DOUBLE PRECISION, -- Price at the time of news (T+0)
    price_1h DOUBLE PRECISION,            -- Price 1 hour later (T+1h)
    price_24h DOUBLE PRECISION            -- Price 24 hours later (T+24h)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_intelligence_timestamp ON intelligence(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_intelligence_urgency ON intelligence(urgency_score DESC);
CREATE INDEX IF NOT EXISTS idx_intelligence_source_id ON intelligence(source_id);
```

## Migration Notes

1.  **JSON Fields**: SQLite stores `summary`, `sentiment`, etc., as TEXT (JSON strings). These must be validated and converted to native `JSONB` in PostgreSQL.
2.  **Timestamps**: SQLite stores strings (e.g., "2023-10-27 10:00:00"). These must be parsed into proper datetime objects with timezone info during migration.
3.  **Dependencies**: The migration script requires `psycopg2-binary` and `sqlite3` (std lib).

## Environment Variables
The application will need the following new env vars:
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_DB`
- `POSTGRES_HOST`
- `POSTGRES_PORT`
