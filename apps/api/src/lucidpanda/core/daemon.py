"""
LucidPanda 单进程守护进程
==========================
scheduler + collector + worker 一体化

架构:
  Scheduler → Collector → Memory Queue → Worker → Result

特性:
- 单进程运行（无 DB 中转）
- 内存队列（低延迟）
- 并发控制（Lane-based）
- 按需采集（16 个原生 RSS 直采）
"""

import asyncio
import time
from datetime import datetime
from typing import Optional
import pytz

from src.lucidpanda.core.logger import logger
from src.lucidpanda.config import settings
from src.lucidpanda.core.collector_v2 import CollectorV2
from src.lucidpanda.core.engine import AlphaEngine


# ──────────────────────────────────────────────────────────────────────
# 配置常量
# ──────────────────────────────────────────────────────────────────────

# 采集间隔
COLLECT_INTERVAL_SECONDS = 120  # 2 分钟

# 并发控制
MAX_QUEUE_SIZE = 100  # 队列最大缓冲 100 条
WORKER_CONCURRENCY = settings.LLM_CONCURRENCY_LIMIT  # 从配置读取（默认 5）

# 健康检查
HEALTH_CHECK_INTERVAL = 60  # 60 秒


class LucidPandaDaemon:
    """
    LucidPanda 单进程守护进程
    
    - Scheduler: 定时调度器
    - Collector: RSS 采集器
    - Worker: AI 分析引擎
    - Queue: 内存队列（解耦）
    """
    
    def __init__(self):
        self.scheduler = None  # 占位，实际用 asyncio.sleep
        self.collector = CollectorV2()
        self.worker = AlphaEngine()
        
        # 内存队列（解耦 collector 和 worker）
        self.queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
        
        # 运行状态
        self.running = False
        self.stats = {
            'collected_count': 0,
            'analyzed_count': 0,
            'queue_size': 0,
            'last_collect_at': None,
            'last_analyze_at': None,
            'errors': 0,
        }
        
        # 并发控制（Lane-based）
        self.collector_semaphore = asyncio.Semaphore(1)  # collector 串行
        self.worker_semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)  # worker 并发
    
    async def initialize(self):
        """初始化组件"""
        logger.info("=" * 70)
        logger.info("   LucidPanda Daemon 启动")
        logger.info("=" * 70)
        logger.info(f"📊 采集间隔：{COLLECT_INTERVAL_SECONDS}秒")
        logger.info(f"🔀 Worker 并发：{WORKER_CONCURRENCY}")
        logger.info(f"📦 队列大小：{MAX_QUEUE_SIZE}")
        logger.info("=" * 70)
        
        # 初始化 collector
        await self.collector.connect()
        logger.info("✅ Collector 已初始化")
        
        # 初始化 worker
        await self.worker.initialize()
        logger.info("✅ Worker 已初始化")
        
        self.running = True
        logger.info("✅ Daemon 已启动")
        logger.info("=" * 70)
    
    async def shutdown(self):
        """优雅关闭"""
        logger.info("🛑 正在停止 Daemon...")
        self.running = False
        
        # 等待队列清空
        if not self.queue.empty():
            logger.info(f"⏳ 等待队列清空 ({self.queue.qsize()} 条)...")
            await asyncio.sleep(5)
        
        # 关闭组件
        await self.collector.disconnect()
        await self.worker.shutdown()
        
        logger.info("✅ Daemon 已停止")
    
    async def collector_loop(self):
        """
        采集器循环（后台运行）
        
        每 2 分钟采集一次 RSS → 放入内存队列
        """
        logger.info("📡 Collector Loop 已启动")
        
        while self.running:
            try:
                # 获取锁（防止并发采集）
                if not self.collector_semaphore.locked():
                    async with self.collector_semaphore:
                        logger.info(f"📡 [轮询] 开始采集 RSS...")
                        
                        # 采集所有信源
                        items = await self._collect_all_feeds()
                        
                        # 放入队列
                        for item in items:
                            try:
                                await self.queue.put(item)
                                self.stats['collected_count'] += 1
                            except asyncio.QueueFull:
                                logger.warning(f"⚠️ 队列已满，丢弃情报")
                                self.stats['errors'] += 1
                        
                        self.stats['last_collect_at'] = datetime.now(pytz.utc).isoformat()
                        self.stats['queue_size'] = self.queue.qsize()
                        
                        logger.info(
                            f"✅ [轮询] 采集完成 | "
                            f"采集：{len(items)} 条 | "
                            f"队列：{self.queue.qsize()}/{MAX_QUEUE_SIZE}"
                        )
                else:
                    logger.debug("⏳ Collector 正在运行，跳过本轮")
                
                # 等待下一轮
                await asyncio.sleep(COLLECT_INTERVAL_SECONDS)
                
            except Exception as e:
                logger.error(f"❌ Collector Loop 异常：{e}")
                self.stats['errors'] += 1
                await asyncio.sleep(30)  # 错误后等待 30 秒
    
    async def _collect_all_feeds(self) -> list:
        """采集所有信源（简化版，直接返回 items）"""
        all_items = []
        
        # 使用 CollectorV2 的采集逻辑
        for feed in self.collector.feed_configs:
            try:
                items = await self.collector.source._fetch_feed_async_wrapper(
                    url=feed['url'],
                    category=feed['category'],
                    name=feed['name']
                )
                all_items.extend(items)
            except Exception as e:
                logger.warning(f"⚠️ [{feed['name']}] 采集失败：{e}")
                self.stats['errors'] += 1
        
        return all_items
    
    async def worker_loop(self):
        """
        Worker 循环（后台运行）
        
        持续从内存队列取数据 → AI 分析 → 保存结果
        """
        logger.info("🤖 Worker Loop 已启动")
        
        while self.running:
            try:
                # 从队列取数据（有数据立即处理，无数据等待）
                try:
                    item = await asyncio.wait_for(
                        self.queue.get(),
                        timeout=10.0  # 10 秒超时
                    )
                except asyncio.TimeoutError:
                    # 队列为空，短暂休息
                    await asyncio.sleep(1)
                    continue
                
                # 并发控制
                if not self.worker_semaphore.locked():
                    async with self.worker_semaphore:
                        # AI 分析
                        try:
                            logger.debug(f"🤖 分析情报：{item.get('id', 'unknown')}")
                            
                            # 调用 worker 分析（简化版）
                            await self._analyze_item(item)
                            
                            self.stats['analyzed_count'] += 1
                            self.stats['last_analyze_at'] = datetime.now(pytz.utc).isoformat()
                            
                            logger.debug(f"✅ 情报分析完成：{item.get('id', 'unknown')}")
                            
                        except Exception as e:
                            logger.error(f"❌ 分析失败 [{item.get('id')}]: {e}")
                            self.stats['errors'] += 1
                
                self.queue.task_done()
                
            except Exception as e:
                logger.error(f"❌ Worker Loop 异常：{e}")
                self.stats['errors'] += 1
                await asyncio.sleep(5)
    
    async def _analyze_item(self, item: dict):
        """分析单条情报（简化版 AlphaEngine）"""
        # 这里调用 AlphaEngine 的分析逻辑
        # 为简化，直接调用 run_once_async 的简化版
        
        # 1. 语义去重
        # is_dup = await self.worker.deduplicator.is_duplicate(item.get('content'))
        # if is_dup:
        #     logger.debug(f"⚠️ 情报重复，跳过：{item.get('id')}")
        #     return
        
        # 2. AI 分析
        # analysis = await self.worker.analyze_intelligence(item)
        
        # 3. 保存结果
        # await self.worker.db.update_intelligence_analysis(item['id'], analysis)
        
        # TODO: 实现完整分析逻辑
        logger.info(f"📊 [分析] {item.get('source', 'unknown')} - {item.get('title', 'unknown')[:50]}...")
        
        # 模拟分析延迟
        await asyncio.sleep(2)
    
    async def health_check_loop(self):
        """健康检查循环（后台运行）"""
        logger.info("💓 Health Check Loop 已启动")
        
        while self.running:
            try:
                await asyncio.sleep(HEALTH_CHECK_INTERVAL)
                
                # 打印统计
                logger.info(
                    f"📊 统计 | "
                    f"采集：{self.stats['collected_count']} | "
                    f"分析：{self.stats['analyzed_count']} | "
                    f"队列：{self.stats['queue_size']} | "
                    f"错误：{self.stats['errors']}"
                )
                
                # 检查队列积压
                if self.queue.qsize() > MAX_QUEUE_SIZE * 0.8:
                    logger.warning(f"⚠️ 队列积压：{self.queue.qsize()}/{MAX_QUEUE_SIZE}")
                
            except Exception as e:
                logger.error(f"❌ Health Check 异常：{e}")
    
    async def run_forever(self):
        """启动主循环"""
        await self.initialize()
        
        # 启动后台任务
        tasks = [
            asyncio.create_task(self.collector_loop()),
            asyncio.create_task(self.worker_loop()),
            asyncio.create_task(self.health_check_loop()),
        ]
        
        logger.info("✅ 所有后台任务已启动")
        logger.info("=" * 70)
        
        try:
            # 等待所有任务（实际是无限运行）
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            logger.info("⌨️  收到停止信号")
        finally:
            await self.shutdown()


# ──────────────────────────────────────────────────────────────────────
# 启动入口
# ──────────────────────────────────────────────────────────────────────

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
    import asyncio
    asyncio.run(main())
