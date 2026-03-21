"""
LucidPanda 单进程守护进程启动脚本
===================================
用法:
    python scripts/core/run_daemon.py
"""
import asyncio
import sys
import os

# 确保项目根目录在 path 中
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.daemon import LucidPandaDaemon


async def main():
    """主函数"""
    daemon = LucidPandaDaemon()
    
    try:
        await daemon.run_forever()
    except KeyboardInterrupt:
        logger.info("⌨️  用户中断")
        await daemon.shutdown()
    except Exception as e:
        logger.error(f"❌ Daemon 异常：{e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
