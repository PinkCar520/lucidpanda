"""
RSSCollector — 情报采集器（生产者）
=====================================
职责单一：拉取所有 RSS 信源 → 过滤 → 入库（status=PENDING）。
不依赖 LLM、推送通道、去重引擎。

与 AlphaEngine（消费者）通过 intelligence 表的 PENDING 状态机解耦：
  collector  → save_raw_intelligence → status=PENDING
  analyzer   → get_pending_intelligence → AI 分析 → status=COMPLETED
"""

import asyncio
from datetime import datetime
import pytz

from src.alphasignal.core.logger import logger
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.config import settings
from src.alphasignal.providers.data_sources.rsshub import RSSHubSource


class RSSCollector:
    """
    独立的 RSS 采集进程。
    每次 collect_once() 拉取全部 Tier-1 feeds，过滤后入库。
    """

    def __init__(self):
        self.db = IntelligenceDB()
        self.source = RSSHubSource(db=self.db)

    async def collect_once(self) -> int:
        """
        执行一轮采集。
        返回本轮新入库条目数。
        """
        logger.info("📡 [Collector] 开始采集 RSS 信源...")

        try:
            items = await self.source.fetch_async()
        except Exception as e:
            logger.error(f"❌ [Collector] RSS 拉取失败: {e}")
            return 0

        if not items:
            logger.info("📡 [Collector] 本轮无新情报")
            return 0

        # URL 唯一性过滤（同一轮内的重复 URL）
        seen_urls: set = set()
        unique_items: list = []
        for item in items:
            url = item.get("url", "") or item.get("id", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)

        # 注入市场快照（此时统一拉取一次，避免每条重复查询）
        now = datetime.now(pytz.utc)
        snapshot = {
            "gold_price_snapshot": self.db.get_market_snapshot("GC=F",      now),
            "dxy_snapshot":        self.db.get_market_snapshot("DX-Y.NYB",  now),
            "us10y_snapshot":      self.db.get_market_snapshot("^TNX",      now),
            "gvz_snapshot":        self.db.get_market_snapshot("^GVZ",      now),
            "oil_price_snapshot":  self.db.get_market_snapshot("CL=F",      now),
        }
        logger.info(
            f"📊 [Collector] 市场快照 | "
            f"Gold={snapshot['gold_price_snapshot']} | "
            f"Oil={snapshot['oil_price_snapshot']} | "
            f"DXY={snapshot['dxy_snapshot']} | "
            f"TNX={snapshot['us10y_snapshot']}"
        )
        for item in unique_items:
            item.setdefault("gold_price_snapshot", snapshot["gold_price_snapshot"])
            item.setdefault("dxy_snapshot",        snapshot["dxy_snapshot"])
            item.setdefault("us10y_snapshot",      snapshot["us10y_snapshot"])
            item.setdefault("gvz_snapshot",        snapshot["gvz_snapshot"])
            item.setdefault("oil_price_snapshot",  snapshot["oil_price_snapshot"])

        # 入库
        saved = 0
        for item in unique_items:
            try:
                row_id = await asyncio.to_thread(self.db.save_raw_intelligence, item)
                if row_id:
                    saved += 1
            except Exception as e:
                logger.error(f"❌ [Collector] 入库失败 [{item.get('id')}]: {e}")

        logger.info(f"✅ [Collector] 本轮入库 {saved} 条（去重后 {len(unique_items)} 条）")
        
        # 触发 Redis 事件驱动唤醒 Worker
        if saved > 0:
            try:
                import redis.asyncio as aioredis
                async with aioredis.from_url(settings.REDIS_URL, decode_responses=True) as r:
                    await r.publish('alphasignal:new_intelligence', str(saved))
                logger.info(f"📣 [Collector] 成功发布 Redis 唤醒事件, 通知 Worker 分析 {saved} 条新数据")
            except Exception as e:
                logger.warning(f"⚠️ [Collector] Redis 事件发布失败 (分析引擎将按 5m 兜底唤醒): {e}")
                
        return saved
