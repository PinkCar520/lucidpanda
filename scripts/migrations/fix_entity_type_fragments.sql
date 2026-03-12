-- 一次性修复：将 entity_type='unknown' 的碎片节点边迁移到对应的规范节点
-- 执行方式：docker exec alphasignal_db psql -U alphasignal alphasignal_core -f /tmp/fix_entity_types.sql

BEGIN;

-- 步骤 1：创建映射表，记录 bad_node_id -> good_node_id
CREATE TEMP TABLE node_mapping AS
SELECT 
    bad.node_id AS bad_id, 
    good.node_id AS good_id
FROM entity_nodes bad
JOIN entity_nodes good 
    ON good.normalized_name = bad.normalized_name 
    AND good.entity_type != 'unknown'
WHERE bad.entity_type = 'unknown';

-- 步骤 2：处理 from_node_id 冲突
-- 删除那些如果更新后会与现有边重复的“坏边”
DELETE FROM entity_edges e
USING node_mapping m, entity_edges existing
WHERE e.from_node_id = m.bad_id
  AND existing.from_node_id = m.good_id
  AND existing.to_node_id = e.to_node_id
  AND existing.relation = e.relation
  AND existing.event_cluster_id = e.event_cluster_id
  AND existing.evidence_source_id = e.evidence_source_id;

-- 1a) 迁移 entity_edges 的 from_node_id
UPDATE entity_edges e
SET from_node_id = m.good_id
FROM node_mapping m
WHERE e.from_node_id = m.bad_id;

-- 步骤 3：处理 to_node_id 冲突
-- 同理，删除更新后会重复的边
DELETE FROM entity_edges e
USING node_mapping m, entity_edges existing
WHERE e.to_node_id = m.bad_id
  AND existing.to_node_id = m.good_id
  AND existing.from_node_id = e.from_node_id
  AND existing.relation = e.relation
  AND existing.event_cluster_id = e.event_cluster_id
  AND existing.evidence_source_id = e.evidence_source_id;

-- 1b) 迁移 entity_edges 的 to_node_id
UPDATE entity_edges e
SET to_node_id = m.good_id
FROM node_mapping m
WHERE e.to_node_id = m.bad_id;

-- 2) 删除已无边的 unknown 节点
DELETE FROM entity_nodes
WHERE node_id IN (SELECT bad_id FROM node_mapping)
  AND node_id NOT IN (
      SELECT from_node_id FROM entity_edges
      UNION
      SELECT to_node_id FROM entity_edges
  );

COMMIT;

-- 验证结果
SELECT entity_name, normalized_name, entity_type, COUNT(*) as edge_count
FROM entity_nodes n
LEFT JOIN entity_edges e ON e.from_node_id = n.node_id OR e.to_node_id = n.node_id
WHERE normalized_name IN ('trump', 'fed', 'gold', 'oil', 'powell', 'usd', 'bitcoin')
GROUP BY entity_name, normalized_name, entity_type
ORDER BY normalized_name, edge_count DESC;
