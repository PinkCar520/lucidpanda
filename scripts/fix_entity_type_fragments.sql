-- 一次性修复：将 entity_type='unknown' 的碎片节点边迁移到对应的规范节点
-- 执行方式：docker exec alphasignal_db psql -U alphasignal alphasignal_core -f /tmp/fix_entity_types.sql

BEGIN;

-- 步骤 1：对每个 normalized_name，找出「主节点」（非 unknown type 中 edge_count 最多的那个）
-- 步骤 2：把所有 unknown 类型节点的边重新指向主节点
-- 步骤 3：删除现在没有边的 unknown 节点

-- 1a) 迁移 entity_edges 的 from_node_id
UPDATE entity_edges e
SET from_node_id = canonical.node_id
FROM (
    SELECT
        bad.node_id AS bad_node_id,
        good.node_id
    FROM entity_nodes bad
    JOIN entity_nodes good
        ON good.normalized_name = bad.normalized_name
        AND good.entity_type != 'unknown'
    WHERE bad.entity_type = 'unknown'
) canonical
WHERE e.from_node_id = canonical.bad_node_id;

-- 1b) 迁移 entity_edges 的 to_node_id
UPDATE entity_edges e
SET to_node_id = canonical.node_id
FROM (
    SELECT
        bad.node_id AS bad_node_id,
        good.node_id
    FROM entity_nodes bad
    JOIN entity_nodes good
        ON good.normalized_name = bad.normalized_name
        AND good.entity_type != 'unknown'
    WHERE bad.entity_type = 'unknown'
) canonical
WHERE e.to_node_id = canonical.bad_node_id;

-- 2) 删除已无边的 unknown 节点（有主节点覆盖的）
DELETE FROM entity_nodes
WHERE entity_type = 'unknown'
  AND normalized_name IN (
      SELECT normalized_name FROM entity_nodes WHERE entity_type != 'unknown'
  )
  AND node_id NOT IN (
      SELECT DISTINCT from_node_id FROM entity_edges
      UNION
      SELECT DISTINCT to_node_id FROM entity_edges
  );

COMMIT;

-- 验证结果
SELECT entity_name, normalized_name, entity_type, COUNT(*) as edge_count
FROM entity_nodes n
LEFT JOIN entity_edges e ON e.from_node_id = n.node_id OR e.to_node_id = n.node_id
WHERE normalized_name IN ('trump', 'fed', 'gold', 'oil', 'powell', 'usd', 'bitcoin')
GROUP BY entity_name, normalized_name, entity_type
ORDER BY normalized_name, edge_count DESC;
