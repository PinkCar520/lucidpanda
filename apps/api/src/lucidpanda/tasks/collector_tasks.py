"""
RSS 采集 Celery 任务
=====================
动态自适应间隔的 RSS 采集任务
"""
import asyncio
import os
import sys
from datetime import datetime
from typing import Dict, Any, List, Optional

from celery import shared_task
from celery_config import app
import redis
import json

# 确保项目路径可用
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.providers.data_sources.rsshub import TIER1_FEEDS_CONFIG, RSSHubSource
from src.lucidpanda.config import settings


# ──────────────────────────────────────────────────────────────────────
# 动态间隔配置
# ──────────────────────────────────────────────────────────────────────

# 默认间隔 (秒)
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

# 间隔边界
MIN_INTERVAL = 30       # 最小 30 秒
MAX_INTERVAL = 1800     # 最大 30 分钟
EMPTY_THRESHOLD = 10    # 连续 10 次空返回后增加间隔


def _get_redis_key(feed_name: str) -> str:
    """获取 Redis 状态键"""
    return f"lucidpanda:feed_state:{feed_name}"


def _get_feed_state(feed_name: str) -> Dict[str, Any]:
    """从 Redis 获取信源状态"""
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = _get_redis_key(feed_name)
    state = r.hgetall(key)
    
    if not state:
        # 初始化状态
        default_interval = DEFAULT_INTERVALS.get(feed_name, 120)
        state = {
            'current_interval': default_interval,
            'consecutive_empty_count': 0,
            'total_fetches': 0,
            'total_new_items': 0,
            'last_fetch_at': '',
            'last_new_item_at': '',
        }
    
    # 类型转换
    state['current_interval'] = int(state.get('current_interval', 120))
    state['consecutive_empty_count'] = int(state.get('consecutive_empty_count', 0))
    state['total_fetches'] = int(state.get('total_fetches', 0))
    state['total_new_items'] = int(state.get('total_new_items', 0))
    
    return state


def _update_feed_state(feed_name: str, state: Dict[str, Any], new_items: int):
    """更新信源状态到 Redis"""
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = _get_redis_key(feed_name)
    
    now = datetime.utcnow().isoformat()
    
    # 更新状态
    state['total_fetches'] += 1
    state['last_fetch_at'] = now
    
    if new_items > 0:
        state['consecutive_empty_count'] = 0
        state['total_new_items'] += new_items
        state['last_new_item_at'] = now
    else:
        state['consecutive_empty_count'] += 1
    
    # 动态调整间隔
    old_interval = state['current_interval']
    new_interval = old_interval
    
    if new_items == 0:
        # 空返回：增加间隔
        if state['consecutive_empty_count'] >= EMPTY_THRESHOLD:
            new_interval = min(old_interval * 2, MAX_INTERVAL)
            if new_interval != old_interval:
                logger.info(f"📈 [{feed_name}] 连续{state['consecutive_empty_count']}次空，间隔调整为{new_interval}s")
    else:
        # 有新增：减少间隔
        state['consecutive_empty_count'] = 0
        new_interval = max(old_interval // 2, MIN_INTERVAL)
        if new_interval != old_interval:
            logger.info(f"📉 [{feed_name}] 采集到{new_items}条，间隔调整为{new_interval}s")
    
    state['current_interval'] = new_interval
    
    # 写入 Redis (7 天过期)
    r.hset(key, mapping={
        'current_interval': state['current_interval'],
        'consecutive_empty_count': state['consecutive_empty_count'],
        'total_fetches': state['total_fetches'],
        'total_new_items': state['total_new_items'],
        'last_fetch_at': state['last_fetch_at'],
        'last_new_item_at': state['last_new_item_at'],
    })
    r.expire(key, 86400 * 7)


def _should_fetch(feed_name: str) -> tuple[bool, int]:
    """判断是否应该采集该信源"""
    state = _get_feed_state(feed_name)
    last_fetch = state.get('last_fetch_at', '')
    current_interval = state['current_interval']
    
    if not last_fetch:
        return True, current_interval
    
    try:
        last_fetch_dt = datetime.fromisoformat(last_fetch)
        elapsed = (datetime.utcnow() - last_fetch_dt).total_seconds()
        
        if elapsed < current_interval:
            # 还没到采集时间
            remaining = current_interval - elapsed
            logger.debug(f"⏭️ [{feed_name}] 跳过采集 (距上次{elapsed:.0f}s < 间隔{current_interval}s, 剩余{remaining:.0f}s)")
            return False, current_interval
    except Exception as e:
        logger.warning(f"⚠️ [{feed_name}] 解析上次采集时间失败：{e}")
    
    return True, current_interval


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_single_feed_task(self, feed_name: str, feed_url: str, category: str) -> Dict[str, Any]:
    """
    单个信源的采集任务

    Args:
        feed_name: 信源名称
        feed_url: RSS URL
        category: 分类 (macro_gold/equity_cn/equity_us)

    Returns:
        {
            'feed_name': str,
            'skipped': bool,
            'new_items': int,
            'saved': int,
            'interval': int,
        }
    """
    import httpx
    import asyncio
    
    db = IntelligenceDB()

    try:
        # 1. 检查是否需要采集
        should_fetch, current_interval = _should_fetch(feed_name)

        if not should_fetch:
            return {
                'feed_name': feed_name,
                'skipped': True,
                'reason': 'not_yet_time',
                'interval': current_interval,
            }

        # 2. 执行采集（直接调用 RSSHubSource 的异步方法）
        source = RSSHubSource(db=db)
        
        # 初始化 semaphore（如果未初始化）
        if source._semaphore is None:
            source._semaphore = asyncio.Semaphore(8)

        _DEFAULT_HEADERS = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }

        async def _fetch():
            async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=True) as client, \
                       httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=False) as ssl_client:
                config = {"name": feed_name, "url": feed_url, "category": category}
                items, _ = await source._fetch_feed_async(client, ssl_client, config)
                return items

        items = asyncio.run(_fetch())
        new_count = len(items) if items else 0

        # 3. 获取/更新状态
        state = _get_feed_state(feed_name)

        # 4. 入库
        saved = 0
        if items:
            for item in items:
                try:
                    row_id = db.save_raw_intelligence(item)
                    if row_id:
                        saved += 1
                except Exception as e:
                    logger.error(f"❌ [{feed_name}] 入库失败 [{item.get('id')}]: {e}")
            
            # 5. 触发 Redis 事件
            if saved > 0:
                try:
                    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                    r.publish('lucidpanda:new_intelligence', str(saved))
                    logger.info(f"📣 [{feed_name}] 发布 Redis 唤醒事件，通知 Worker 分析 {saved} 条")
                except Exception as e:
                    logger.warning(f"⚠️ [{feed_name}] Redis 事件发布失败：{e}")
        
        # 6. 更新状态
        _update_feed_state(feed_name, state, saved)
        
        # 7. 日志
        if saved > 0:
            logger.info(f"✅ [{feed_name}] 采集成功：{saved}条新情报 (间隔:{state['current_interval']}s)")
        else:
            logger.debug(f"🧪 [{feed_name}] 采集完成：无新情报 (间隔:{state['current_interval']}s)")
        
        return {
            'feed_name': feed_name,
            'skipped': False,
            'new_items': new_count,
            'saved': saved,
            'interval': state['current_interval'],
        }
        
    except Exception as e:
        logger.error(f"❌ [{feed_name}] 采集失败：{e}")
        # 重试
        raise self.retry(exc=e, countdown=60)


@app.task(bind=True, max_retries=3, default_retry_delay=60)
def fetch_all_feeds(self) -> Dict[str, Any]:
    """
    采集所有信源（由 Celery Beat 每分钟调用）

    内部会判断每个信源是否真的需要采集（基于动态间隔）
    
    注意：不能在任务内部调用 .get()，改用 chord 回调模式

    Returns:
        汇总统计
    """
    from celery import chord
    
    logger.info("🔄 [Celery] 开始执行全量信源采集检查...")
    
    # 并行采集所有信源
    tasks = []
    for feed in TIER1_FEEDS_CONFIG:
        # 检查是否需要采集
        should_fetch, _ = _should_fetch(feed['name'])
        if should_fetch:
            tasks.append(
                fetch_single_feed_task.s(
                    feed['name'],
                    feed['url'],
                    feed['category']
                )
            )
    
    if not tasks:
        logger.info("📊 [Celery] 所有信源都未到采集时间，跳过本轮")
        return {
            'total_feeds': len(TIER1_FEEDS_CONFIG),
            'fetched': 0,
            'skipped': len(TIER1_FEEDS_CONFIG),
            'total_new_items': 0,
            'errors': 0,
        }
    
    # 使用 chord 并行执行，结果由回调函数 aggregate_results 处理
    # 注意：这里不能调用 .get()，直接返回任务信息
    chord(tasks)(aggregate_results.s())
    
    return {
        'total_feeds': len(TIER1_FEEDS_CONFIG),
        'fetched': len(tasks),
        'skipped': len(TIER1_FEEDS_CONFIG) - len(tasks),
        'total_new_items': 0,  # 实际结果由回调函数处理
        'errors': 0,
        'status': 'processing',
    }


@app.task
def aggregate_results(results):
    """
    聚合所有采集任务的结果
    
    Args:
        results: 所有 fetch_single_feed_task 的返回值列表
    """
    summary = {
        'total_feeds': len(results),
        'fetched': 0,
        'skipped': 0,
        'total_new_items': 0,
        'errors': 0,
    }
    
    for result in results:
        if isinstance(result, dict):
            if result.get('error'):
                summary['errors'] += 1
            elif result.get('skipped'):
                summary['skipped'] += 1
            else:
                summary['fetched'] += 1
                summary['total_new_items'] += result.get('saved', 0)
    
    logger.info(
        f"📊 [Celery] 全量采集完成："
        f"total={summary['total_feeds']} | "
        f"fetched={summary['fetched']} | "
        f"skipped={summary['skipped']} | "
        f"new_items={summary['total_new_items']} | "
        f"errors={summary['errors']}"
    )
    
    return summary
