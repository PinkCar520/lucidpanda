"""
RSSCollector V2 — 改进版情报采集器
=====================================
特性:
- 并发控制（Semaphore 限制最大并发数）
- 失败重试（指数退避策略）
- 动态间隔（每个信源独立配置采集频率）
- 统计监控（记录成功率、耗时等指标）
"""

import asyncio
import time
import redis.asyncio as redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
import pytz

from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.config import settings
from src.lucidpanda.providers.data_sources.rsshub import RSSHubSource, TIER1_FEEDS_CONFIG


# ──────────────────────────────────────────────────────────────────────
# 配置常量
# ──────────────────────────────────────────────────────────────────────

# 默认采集间隔（秒）
DEFAULT_INTERVALS = {
    # Tier-1: 高频快讯 (60 秒)
    "财联社 - 电报": 60,
    "财联社 - 深度": 120,
    "证券时报 - 网快讯": 120,

    # Tier-2: 中频新闻 (300 秒)
    "Bloomberg Economics": 300,
    "Bloomberg Markets": 300,
    "WSJ Economy": 300,
    "WSJ Markets": 300,
    "CNBC Technology": 300,
    "Reuters-Business": 300,
    "MarketWatch-Top": 300,
    "Yahoo Finance-News": 300,
    "Politico Politics": 300,

    # Tier-3: 低频官方 (900 秒)
    "WhiteHouse Exec Orders": 900,
    "Fed Speeches": 900,
    "Fed Press Releases": 900,
    "CFTC Press Releases": 900,
    "Trump Truth Social": 300,

    # A 股政策 (180 秒)
    "华尔街见闻-A 股": 180,
    "上交所 - 信息披露": 300,
    "深交所 - 上市公告": 300,
}

# 并发控制
MAX_CONCURRENT = 5  # 最大同时采集 5 个信源

# 重试配置
MAX_RETRIES = 3
RETRY_BASE_DELAY = 30  # 基础延迟 30 秒

# Redis Key 前缀
REDIS_PREFIX = "lucidpanda:collector:"


@dataclass
class FeedStats:
    """信源统计信息"""
    feed_name: str
    last_fetch_at: Optional[str] = None
    last_success_at: Optional[str] = None
    last_error_at: Optional[str] = None
    last_error: Optional[str] = None
    consecutive_failures: int = 0
    total_fetches: int = 0
    total_successes: int = 0
    total_items: int = 0
    avg_duration_ms: float = 0.0
    current_interval: int = 120


class CollectorV2:
    """
    改进版 RSS 采集器
    
    特性:
    - 并发控制：Semaphore 限制最大并发数
    - 失败重试：指数退避策略
    - 动态间隔：每个信源独立配置
    - 统计监控：记录成功率、耗时等
    """
    
    def __init__(self):
        self.db = IntelligenceDB()
        self.source = RSSHubSource(db=self.db)
        self.redis_client: Optional[redis.Redis] = None
        self.semaphore = asyncio.Semaphore(MAX_CONCURRENT)
        self.running = False
        
        # 信源配置
        self.feed_configs = TIER1_FEEDS_CONFIG
        
        # 统计缓存
        self.stats_cache: Dict[str, FeedStats] = {}
    
    async def connect(self):
        """连接 Redis"""
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        logger.info(f"✅ 已连接 Redis: {settings.REDIS_URL}")
    
    async def disconnect(self):
        """断开连接"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("🔌 已断开 Redis 连接")
    
    def _get_interval(self, feed_name: str) -> int:
        """获取信源采集间隔"""
        return DEFAULT_INTERVALS.get(feed_name, 300)
    
    async def _get_feed_stats(self, feed_name: str) -> FeedStats:
        """从 Redis 获取信源统计"""
        key = f"{REDIS_PREFIX}stats:{feed_name}"
        data = await self.redis_client.hgetall(key)
        
        if not data:
            return FeedStats(
                feed_name=feed_name,
                current_interval=self._get_interval(feed_name)
            )
        
        # 转换类型
        return FeedStats(
            feed_name=feed_name,
            last_fetch_at=data.get('last_fetch_at'),
            last_success_at=data.get('last_success_at'),
            last_error_at=data.get('last_error_at'),
            last_error=data.get('last_error'),
            consecutive_failures=int(data.get('consecutive_failures', 0)),
            total_fetches=int(data.get('total_fetches', 0)),
            total_successes=int(data.get('total_successes', 0)),
            total_items=int(data.get('total_items', 0)),
            avg_duration_ms=float(data.get('avg_duration_ms', 0)),
            current_interval=int(data.get('current_interval', 120))
        )
    
    async def _save_feed_stats(self, stats: FeedStats):
        """保存信源统计到 Redis"""
        key = f"{REDIS_PREFIX}stats:{stats.feed_name}"
        await self.redis_client.hset(key, mapping=asdict(stats))
        await self.redis_client.expire(key, 86400 * 7)  # 7 天过期
    
    async def _fetch_with_retry(self, feed_config: Dict[str, Any]) -> Optional[int]:
        """
        采集单个信源（带重试）
        
        Returns:
            新增条目数，失败返回 None
        """
        feed_name = feed_config['name']
        url = feed_config['url']
        category = feed_config['category']
        
        stats = await self._get_feed_stats(feed_name)
        
        for attempt in range(MAX_RETRIES):
            start_time = time.time()
            
            try:
                async with self.semaphore:
                    logger.info(
                        f"📡 [{feed_name}] 开始采集 (尝试 {attempt + 1}/{MAX_RETRIES}) "
                        f"[并发：{MAX_CONCURRENT}]"
                    )
                    
                    # 执行采集
                    items = await self.source._fetch_feed_async_wrapper(url, category)
                    
                    duration_ms = (time.time() - start_time) * 1000
                    
                    # 更新统计
                    stats.last_fetch_at = datetime.now(pytz.utc).isoformat()
                    stats.total_fetches += 1
                    stats.avg_duration_ms = (
                        (stats.avg_duration_ms * (stats.total_fetches - 1) + duration_ms)
                        / stats.total_fetches
                    )
                    
                    if items:
                        # 采集成功
                        stats.last_success_at = stats.last_fetch_at
                        stats.consecutive_failures = 0
                        stats.total_successes += 1
                        stats.total_items += len(items)
                        
                        logger.info(
                            f"✅ [{feed_name}] 采集成功 | "
                            f"{len(items)} 条目 | {duration_ms:.0f}ms"
                        )
                        
                        # 保存到数据库
                        saved = await self._save_items(items)
                        return saved
                    else:
                        # 空返回（不算失败）
                        stats.consecutive_failures = 0
                        logger.info(f"⚠️ [{feed_name}] 采集结果为空")
                        return 0
                    
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                # 更新统计
                stats.last_fetch_at = datetime.now(pytz.utc).isoformat()
                stats.last_error_at = stats.last_fetch_at
                stats.last_error = str(e)
                stats.consecutive_failures += 1
                stats.total_fetches += 1
                
                logger.warning(
                    f"⚠️ [{feed_name}] 采集失败 (尝试 {attempt + 1}/{MAX_RETRIES}): {e}"
                )
                
                if attempt < MAX_RETRIES - 1:
                    # 指数退避
                    delay = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.info(f"⏳ [{feed_name}] {delay}秒后重试...")
                    await asyncio.sleep(delay)
                else:
                    # 放弃
                    logger.error(f"❌ [{feed_name}] 重试{MAX_RETRIES}次后放弃")
        
        # 保存统计
        await self._save_feed_stats(stats)
        return None
    
    async def _save_items(self, items: List[Dict]) -> int:
        """保存情报到数据库"""
        saved = 0
        seen_urls = set()
        
        for item in items:
            url = item.get("url", "") or item.get("id", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                try:
                    row_id = await asyncio.to_thread(self.db.save_raw_intelligence, item)
                    if row_id:
                        saved += 1
                except Exception as e:
                    logger.error(f"❌ 入库失败 [{item.get('id')}]: {e}")
        
        return saved
    
    async def _should_fetch(self, feed_name: str) -> bool:
        """检查信源是否需要采集"""
        stats = await self._get_feed_stats(feed_name)
        
        if not stats.last_fetch_at:
            return True
        
        last_fetch = datetime.fromisoformat(stats.last_fetch_at.replace('Z', '+00:00'))
        now = datetime.now(pytz.utc)
        elapsed = (now - last_fetch).total_seconds()
        
        return elapsed >= stats.current_interval
    
    async def run_forever(self):
        """启动采集器主循环"""
        self.running = True
        logger.info("=" * 60)
        logger.info("   LucidPanda Collector V2 启动")
        logger.info("=" * 60)
        logger.info(f"📊 信源数量：{len(self.feed_configs)}")
        logger.info(f"🔀 最大并发：{MAX_CONCURRENT}")
        logger.info(f"🔄 重试次数：{MAX_RETRIES}")
        logger.info(f"⏱️  基础延迟：{RETRY_BASE_DELAY}秒")
        logger.info("=" * 60)
        
        loop_count = 0
        
        while self.running:
            loop_start = time.time()
            loop_count += 1
            
            try:
                # 1. 找出所有到期的信源
                due_feeds = []
                for feed in self.feed_configs:
                    if await self._should_fetch(feed['name']):
                        due_feeds.append(feed)
                
                if not due_feeds:
                    logger.debug(f"⏳ [轮询{loop_count}] 所有信源未到采集时间，10 秒后检查")
                    await asyncio.sleep(10)
                    continue
                
                logger.info(
                    f"🚀 [轮询{loop_count}] 开始采集 | "
                    f"到期信源：{len(due_feeds)}/{len(self.feed_configs)}"
                )
                
                # 2. 并发采集
                tasks = [self._fetch_with_retry(feed) for feed in due_feeds]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # 3. 统计结果
                total_saved = sum(r for r in results if isinstance(r, int))
                errors = sum(1 for r in results if isinstance(r, Exception))
                
                loop_duration = time.time() - loop_start
                
                logger.info(
                    f"✅ [轮询{loop_count}] 采集完成 | "
                    f"入库：{total_saved} 条 | 错误：{errors} | "
                    f"耗时：{loop_duration:.1f}秒"
                )
                
                # 4. 短暂休息
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"❌ [轮询{loop_count}] 主循环异常：{e}")
                await asyncio.sleep(30)
    
    async def stop(self):
        """停止采集器"""
        self.running = False
        logger.info("🛑 采集器停止中...")


# ──────────────────────────────────────────────────────────────────────
# 启动脚本
# ──────────────────────────────────────────────────────────────────────

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
