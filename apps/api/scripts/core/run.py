import asyncio
import os
import sys

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.config import settings  # noqa: E402
from src.lucidpanda.core.engine import AlphaEngine  # noqa: E402
from src.lucidpanda.core.logger import logger  # noqa: E402


async def main_loop():
    logger.info("==========================================")
    logger.info("   LucidPanda 2.0 - 智能情报流处理系统启动")
    logger.info("==========================================")
    fallback_timeout = 300  # 5分钟兜底轮询

    logger.info(f"流式模式: Redis Pub/Sub 事件驱动 (兜底间隔: {fallback_timeout//60} 分钟)")
    logger.info(f"AI 引擎并发数: {settings.LLM_CONCURRENCY_LIMIT}")

    # 初始化 Redis 异步连接
    import redis.asyncio as redis
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("lucidpanda:new_intelligence")
    logger.info("📡 已订阅 Redis 频道: lucidpanda:new_intelligence (事件驱动唤醒)")


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
            if pubsub:
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=fallback_timeout)
                if message:
                    logger.info(f"⚡ 收到事件唤醒信号: {message['data']} - 立即启动分析")
            else:
                # Pubsub 丢失，强行触发兜底
                await asyncio.sleep(fallback_timeout)
        except Exception as e:
            logger.warning(f"Redis 监听异常: {e}，将尝试重建连接并回退到 {fallback_timeout}s Sleep")
            # 尝试销毁旧连接对象，下一次大循环时重建
            try:
                if pubsub:
                    await pubsub.close()
            except Exception as e:
                logger.debug(f"关闭 Redis pubsub 异常: {e}")
            pubsub = None
            redis_client = None

            await asyncio.sleep(fallback_timeout)

            # 兜底重建 Redis 连接
            try:
                import redis.asyncio as redis_module
                redis_client = redis_module.from_url(settings.REDIS_URL, decode_responses=True)
                pubsub = redis_client.pubsub()
                await pubsub.subscribe("lucidpanda:new_intelligence")
                logger.info("📡 已重新订阅 Redis 频道: lucidpanda:new_intelligence")
            except Exception as re_e:
                logger.error(f"❌ 重新订阅 Redis 失败: {re_e}")

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("系统停止运行")
