import asyncio
import sys
import os

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.alphasignal.core.logger import logger
from src.alphasignal.core.rss_collector import RSSCollector
from src.alphasignal.providers.data_sources.rsshub import TIER1_FEEDS_CONFIG

# 采集间隔：比分析引擎更频繁（2分钟），确保 PENDING 队列始终有新鲜数据
_COLLECT_INTERVAL_SECONDS = 120


async def collector_loop():
    logger.info("==========================================")
    logger.info("   AlphaSignal - RSS 情报采集器 启动")
    logger.info("==========================================")
    logger.info(f"采集间隔: {_COLLECT_INTERVAL_SECONDS}s | 信源数: {len(TIER1_FEEDS_CONFIG)}")

    collector = RSSCollector()

    while True:
        try:
            await collector.collect_once()
        except Exception as e:
            logger.error(f"[Collector] 主循环异常: {e}")

        await asyncio.sleep(_COLLECT_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(collector_loop())
    except KeyboardInterrupt:
        logger.info("[Collector] 停止运行")
