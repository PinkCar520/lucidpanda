-- =====================================================
-- 基金自选列表升级迁移脚本
-- 版本：v2.0
-- 日期：2026-02-22
-- 目标：保留所有旧数据，添加分组、排序、同步功能
-- =====================================================

-- 开始事务
BEGIN;

-- 1. 创建分组表 (watchlist_groups)
CREATE TABLE IF NOT EXISTS watchlist_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(50) NOT NULL,
    icon VARCHAR(50) DEFAULT 'folder',
    color VARCHAR(20) DEFAULT '#007AFF',
    sort_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_groups_user ON watchlist_groups(user_id, sort_index);
CREATE UNIQUE INDEX IF NOT EXISTS idx_groups_user_name ON watchlist_groups(user_id, name);

-- 2. 创建同步日志表 (watchlist_sync_log)
CREATE TABLE IF NOT EXISTS watchlist_sync_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    operation_type VARCHAR(20) NOT NULL,
    fund_code VARCHAR(20) NOT NULL,
    old_value JSONB,
    new_value JSONB,
    device_id VARCHAR(50),
    client_timestamp TIMESTAMPTZ NOT NULL,
    server_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_synced BOOLEAN DEFAULT FALSE
);

CREATE INDEX IF NOT EXISTS idx_sync_log_user ON watchlist_sync_log(user_id, is_synced);
CREATE INDEX IF NOT EXISTS idx_sync_log_time ON watchlist_sync_log(client_timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_sync_log_synced ON watchlist_sync_log(is_synced);
CREATE INDEX IF NOT EXISTS idx_sync_log_user_time ON watchlist_sync_log(user_id, client_timestamp DESC);

-- 3. 创建临时表 (新结构)
CREATE TABLE fund_watchlist_new (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    fund_code VARCHAR(20) NOT NULL,
    fund_name VARCHAR(100) NOT NULL,
    group_id UUID REFERENCES watchlist_groups(id) ON DELETE SET NULL,
    sort_index INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    UNIQUE(user_id, fund_code)
);

CREATE INDEX IF NOT EXISTS idx_fund_watchlist_user ON fund_watchlist_new(user_id, is_deleted);
CREATE INDEX IF NOT EXISTS idx_fund_watchlist_group ON fund_watchlist_new(group_id);
CREATE INDEX IF NOT EXISTS idx_fund_watchlist_user_sort ON fund_watchlist_new(user_id, sort_index);

-- 4. 迁移旧数据到新表
-- 注意：这里假设 users 表的 id 与旧表 fund_watchlist.user_id 都是 UUID 类型
-- 如果旧表的 user_id 是其他格式，需要调整 JOIN 逻辑

-- 先为每个有自选的用户创建默认分组
INSERT INTO watchlist_groups (user_id, name, icon, color, sort_index)
SELECT DISTINCT 
    u.id,
    '默认分组',
    'star',
    '#007AFF',
    0
FROM fund_watchlist fw
JOIN users u ON u.id = fw.user_id
ON CONFLICT (user_id, name) DO NOTHING;

-- 迁移数据，将旧数据分配到默认分组
INSERT INTO fund_watchlist_new (user_id, fund_code, fund_name, group_id, created_at, sort_index)
SELECT 
    u.id,
    fw.fund_code,
    fw.fund_name,
    wg.id as group_id,
    fw.created_at,
    ROW_NUMBER() OVER (PARTITION BY fw.user_id ORDER BY fw.created_at) - 1 as sort_index
FROM fund_watchlist fw
JOIN users u ON u.id = fw.user_id
LEFT JOIN watchlist_groups wg ON wg.user_id = u.id AND wg.name = '默认分组';

-- 5. 备份旧表
ALTER TABLE fund_watchlist RENAME TO fund_watchlist_old;

-- 6. 重命名新表
ALTER TABLE fund_watchlist_new RENAME TO fund_watchlist;

-- 7. 创建触发器 (自动更新 updated_at)
CREATE OR REPLACE FUNCTION update_watchlist_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_watchlist_update ON fund_watchlist;

CREATE TRIGGER trg_watchlist_update
BEFORE UPDATE ON fund_watchlist
FOR EACH ROW
EXECUTE FUNCTION update_watchlist_timestamp();

-- 8. 验证数据
DO $$
DECLARE
    old_count INTEGER;
    new_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO old_count FROM fund_watchlist_old;
    SELECT COUNT(*) INTO new_count FROM fund_watchlist;
    
    RAISE NOTICE '旧表记录数：%', old_count;
    RAISE NOTICE '新表记录数：%', new_count;
    
    IF old_count != new_count THEN
        RAISE WARNING '数据迁移后记录数不匹配！旧：% 新：%', old_count, new_count;
    ELSE
        RAISE NOTICE '数据迁移成功，记录数匹配';
    END IF;
END $$;

-- 提交事务
COMMIT;

-- =====================================================
-- 回滚脚本 (如果需要)
-- =====================================================
-- 注意：回滚需要在事务外执行
-- 
-- BEGIN;
-- DROP TABLE IF EXISTS fund_watchlist;
-- ALTER TABLE fund_watchlist_old RENAME TO fund_watchlist;
-- DROP TABLE IF EXISTS watchlist_groups;
-- DROP TABLE IF EXISTS watchlist_sync_log;
-- DROP FUNCTION IF EXISTS update_watchlist_timestamp();
-- COMMIT;
