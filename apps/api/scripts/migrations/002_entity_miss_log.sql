-- Phase 2: Entity Miss Logging
-- 记录未匹配到 Canonical ID 的原生实体名，协助运维人员快速补充词典。

CREATE TABLE IF NOT EXISTS entity_miss_log (
    id SERIAL PRIMARY KEY,
    raw_entity_name TEXT UNIQUE NOT NULL,
    last_source_id TEXT,
    occurrence_count INT DEFAULT 1,
    first_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_seen TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 加快审核界面拉取速度
CREATE INDEX IF NOT EXISTS idx_entity_miss_last_seen ON entity_miss_log(last_seen DESC);
