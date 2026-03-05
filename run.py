import asyncio
import sys
import os

# 确保 src 目录在 path 中
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.core.engine import AlphaEngine

async def main_loop():
    logger.info("==========================================")
    logger.info("   AlphaSignal 2.0 - 智能情报流处理系统启动")
    logger.info("==========================================")
    fallback_timeout = 300  # 5分钟兜底轮询

    logger.info(f"流式模式: Redis Pub/Sub 事件驱动 (兜底间隔: {fallback_timeout//60} 分钟)")
    logger.info(f"AI 引擎并发数: 5")

    # 初始化 Redis 异步连接
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("alphasignal:new_intelligence")
    logger.info("📡 已订阅 Redis 频道: alphasignal:new_intelligence (事件驱动唤醒)")


    engine = AlphaEngine()

    while True:
        try:
            # 执行异步扫描
            await engine.run_once_async()
        except Exception as e:
            logger.error(f"主循环异常: {e}")
        
        logger.info(f"📡 等候新数据事件(Redis) 或 {fallback_timeout}s 兜底自动轮询...")
        
        try:
            # 阻塞等待 Redis 消息，或超时自动唤醒
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=fallback_timeout)
            if message:
                logger.info(f"⚡ 收到事件唤醒信号: {message['data']} - 立即启动分析")
        except Exception as e:
            logger.warning(f"Redis 监听异常: {e}，将回退到 {fallback_timeout}s Sleep")
            await asyncio.sleep(fallback_timeout)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("系统停止运行")
