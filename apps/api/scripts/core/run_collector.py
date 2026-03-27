"""
RSS 采集器 - Celery 版本
========================
注意：此脚本现在仅用于向后兼容。
Celery 集成后，采集任务由 celery_beat + celery_worker 执行。

使用方法:
- 传统模式 (不推荐): python scripts/core/run_collector.py
- Celery 模式 (推荐): docker compose up celery_beat celery_worker
"""
import asyncio
import sys
import os

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.rss_collector import RSSCollector
from src.lucidpanda.providers.data_sources.rsshub import TIER1_FEEDS_CONFIG

# 采集间隔：比分析引擎更频繁（2 分钟），确保 PENDING 队列始终有新鲜数据
# 注意：Celery 集成后，此间隔由动态自适应算法自动调整
_COLLECT_INTERVAL_SECONDS = 120


async def collector_loop():
    logger.info("==========================================")
    logger.info("   LucidPanda - RSS 情报采集器 启动")
    logger.info("==========================================")
    logger.warning("⚠️  注意：此脚本已过时，建议使用 Celery 模式")
    logger.warning("⚠️  启动命令：docker compose up celery_beat celery_worker")
    logger.info("==========================================")
    logger.info(f"采集间隔：{_COLLECT_INTERVAL_SECONDS}s | 信源数：{len(TIER1_FEEDS_CONFIG)}")

    collector = RSSCollector()

    while True:
        try:
            await collector.collect_once()
        except Exception as e:
            logger.error(f"[Collector] 主循环异常：{e}")

        await asyncio.sleep(_COLLECT_INTERVAL_SECONDS)


if __name__ == "__main__":
    logger.warning("⚠️  使用传统采集模式，建议使用 Celery 模式以获得更好的性能")
    try:
        asyncio.run(collector_loop())
    except KeyboardInterrupt:
        logger.info("[Collector] 停止运行")
