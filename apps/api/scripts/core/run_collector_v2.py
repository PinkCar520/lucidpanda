"""
RSS 采集器 V2 - 改进版
======================
特性:
- 并发控制（最大 5 并发）
- 失败重试（指数退避）
- 动态间隔（每个信源独立配置）
- 统计监控（Redis 存储）
"""
import asyncio
import sys
import os

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.core.collector_v2 import CollectorV2
from src.lucidpanda.core.logger import logger


async def main():
    """主函数"""
    collector = CollectorV2()
    
    try:
        await collector.connect()
        await collector.run_forever()
    except KeyboardInterrupt:
        logger.info("⌨️  用户中断，正在停止...")
        await collector.stop()
    except Exception as e:
        logger.error(f"❌ 采集器异常：{e}")
        raise
    finally:
        await collector.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
