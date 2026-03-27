"""
core/event_clusterer.py — 事件聚类器
======================================
对一批 PENDING 情报记录进行事件聚类：
  - 同一事件（多信源）被归入同一 cluster
  - 每个 cluster 选出最优 lead（信源可信度最高，或最早到达）
  - 非 lead 记录标记为 CLUSTERED，跳过 AI 分析和推送

算法：
  1. 通过 pg_trgm 在 DB 内找相似对（单次查询）
  2. Python Union-Find 分组
  3. 按 source_credibility_score DESC → timestamp ASC 选 lead
"""

import uuid

from src.lucidpanda.core.logger import logger

# ── Union-Find ────────────────────────────────────────────────────────────────


class _UnionFind:
    def __init__(self, items: list):
        self._parent = {x: x for x in items}

    def find(self, x):
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path compression
            x = self._parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self._parent[rb] = ra

    def groups(self) -> dict[str, list]:
        """Return {root: [members...]} only for groups with > 1 member."""
        g: dict[str, list] = {}
        for x in self._parent:
            root = self.find(x)
            g.setdefault(root, []).append(x)
        return {r: m for r, m in g.items() if len(m) > 1}


# ── EventClusterer ────────────────────────────────────────────────────────────


class EventClusterer:
    """
    使用示例（在 engine.run_once_async 中）：

        clusterer = EventClusterer(db=self.db)
        leads, n_suppressed = clusterer.cluster(pending_records)
        # leads: 只需要 AI 分析的记录列表
        # n_suppressed: 被压制的记录数
    """

    # pg_trgm / HNSW 相似度阈值（0.40 对应新闻聚类，开启衰减后稍微放宽以支持长线追踪）
    SIMILARITY_THRESHOLD: float = 0.40
    # 事件时间窗口（小时）：支持跨 48h 的长线故事追踪 (Story Threading)
    TIME_WINDOW_HOURS: int = 48

    def __init__(self, db):
        """
        Args:
            db: IntelligenceDB 实例（持有 find_similar_pairs / mark_clustered）
        """
        self.db = db

    def cluster(self, pending_items: list[dict]) -> tuple[list[dict], list[dict]]:
        """
        对 PENDING 记录进行事件聚类。

        Args:
            pending_items: get_pending_intelligence() 返回的记录列表，
                           每条至少含 source_id, content, timestamp,
                           source_credibility_score (可为 None)

        Returns:
            (lead_items, follower_items)
            lead_items    — 需要进全量 AI 分析的记录（每事件仅 1 条）
            follower_items — 注入了 parent_lead_id 的跟进报道，用于提取 Delta
        """
        if len(pending_items) < 2:
            return pending_items, 0

        source_ids = [item.get("source_id") or item.get("id") for item in pending_items]

        # Step 1: DB 内找相似对（单次 SQL）
        pairs = self.db.find_similar_pairs(
            source_ids,
            threshold=self.SIMILARITY_THRESHOLD,
            time_window_hours=self.TIME_WINDOW_HOURS,
        )

        if not pairs:
            return pending_items, 0

        logger.info(f"🔍 事件聚类：发现 {len(pairs)} 对相似情报，开始分组...")

        # Step 2: Union-Find 分组
        uf = _UnionFind(source_ids)
        for a, b in pairs:
            uf.union(a, b)

        clusters = uf.groups()  # {root: [sid1, sid2, ...]}
        if not clusters:
            return pending_items, 0

        # Step 3: 为每个 cluster 选 lead，将其余标记为 CLUSTERED
        # 建 sid → record 查找表
        sid_to_item = {
            (item.get("source_id") or item.get("id")): item for item in pending_items
        }

        suppressed_sids: set[str] = set()

        for group_members in clusters.values():
            cluster_id = str(uuid.uuid4())
            lead_sid = self._pick_lead(group_members, sid_to_item)
            follower_sids = [s for s in group_members if s != lead_sid]

            # 写 DB（异步 IO 由 engine 用 asyncio.to_thread 包裹）
            self.db.mark_clustered(group_members, cluster_id, lead_sid)
            suppressed_sids.update(follower_sids)

            # 为 follower 字典注入 parent_lead_id
            for fsid in follower_sids:
                if fsid in sid_to_item:
                    sid_to_item[fsid]["parent_lead_id"] = lead_sid
                    sid_to_item[fsid]["parent_story_id"] = cluster_id

        # Step 4: 过滤返回仅 lead 记录和 follower 记录
        lead_items = [
            item
            for item in pending_items
            if (item.get("source_id") or item.get("id")) not in suppressed_sids
        ]
        follower_items = [
            item
            for item in pending_items
            if (item.get("source_id") or item.get("id")) in suppressed_sids
        ]

        logger.info(
            f"✅ 事件聚类完成 | 本轮 {len(pending_items)} 条 → "
            f"{len(lead_items)} lead + {len(follower_items)} followers (进入 Delta 检查)"
        )
        return lead_items, follower_items

    async def rebuild_story_threading_history_async(self, limit: int = 5000):
        """
        [运维/迁移工具] 为历史数据补全 story_id 和 is_story_lead。
        针对已经 COMPLETED 但 story_id 为空的存量记录，进行回溯式聚类。
        """
        import asyncio
        import uuid

        logger.info(f"⏳ 开始执行历史故事线回填，目标限额：{limit}...")

        # 1. 查找缺失 story_id 的存量记录
        query = """
            SELECT source_id, content, timestamp, source_credibility_score 
            FROM intelligence 
            WHERE status = 'COMPLETED' AND story_id IS NULL 
            ORDER BY timestamp DESC LIMIT %s
        """
        records = await asyncio.to_thread(self.db.query, query, (limit,))

        if not records:
            logger.info("✅ 没有发现缺失故事线的历史记录，跳过回填。")
            return

        logger.info(
            f"📚 发现 {len(records)} 条待处理历史记录，正在进行追溯性聚类分析..."
        )

        # 2. 调用标准聚类逻辑
        lead_items, follower_items = self.cluster(records)

        # 3. 为 Lead 记录打上标记
        for lead in lead_items:
            sid = lead.get("source_id") or lead.get("id")
            # 使用 SID 派生确定性的 Story ID (或随机，此处为了回溯一致性使用随机 UUID4)
            story_id = str(uuid.uuid4())
            await asyncio.to_thread(
                self.db.execute,
                "UPDATE intelligence SET story_id = %s, is_story_lead = TRUE WHERE source_id = %s",
                (story_id, sid),
            )

        logger.info(
            f"✨ 历史回填完成 | 本轮处理: {len(records)} | 形成故事主线: {len(lead_items)}"
        )

    # ── 内部 ──────────────────────────────────────────────────────────────

    def _pick_lead(self, member_sids: list[str], sid_to_item: dict) -> str:
        """
        Lead 选择策略（优先级从高到低）：
          1. source_credibility_score 最高（历史准确率）
          2. timestamp 最早（最先报道）
          3. source_id 字典序（兜底确定性排序）
        """

        def sort_key(sid: str):
            item = sid_to_item.get(sid, {})
            credibility = item.get("source_credibility_score") or 0.0
            ts = item.get("timestamp")
            # 越高越好 → 负号；timestamp 越早越好 → 原值
            return (-credibility, ts or "", sid)

        return min(member_sids, key=sort_key)
