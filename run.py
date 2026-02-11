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
    logger.info(f"流式轮询间隔: {settings.CHECK_INTERVAL_MINUTES} 分钟 (异步)")
    logger.info(f"AI 引擎并发数: 5")

    engine = AlphaEngine()

    while True:
        try:
            # 执行异步扫描
            await engine.run_once_async()
        except Exception as e:
            logger.error(f"主循环异常: {e}")
        
        # 即使间隔设为 2 分钟，我们也可以让它更频繁地检查“补课”记录
        # 如果有待补课记录，缩短 sleep 时间
        sleep_time = settings.CHECK_INTERVAL_MINUTES * 60
        logger.debug(f"等候 {sleep_time} 秒进行下一轮扫描...")
        await asyncio.sleep(sleep_time)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("系统停止运行")
