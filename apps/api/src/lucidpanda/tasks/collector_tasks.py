"""
TaskIQ 纯异步采集任务模块
=========================
弃用旧版 Celery 同步阻塞模式，采用原生 async/await
"""
import asyncio
import json
import os
import sys
from datetime import datetime
from typing import Any

import httpx
import redis

# 确保项目路径可用
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.config import settings
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.logger import logger

# 引入 TaskIQ broker
from src.lucidpanda.core.taskiq_broker import broker
from src.lucidpanda.providers.data_sources.rsshub import (
    TIER1_FEEDS_CONFIG,
    RSSHubSource,
)

# ──────────────────────────────────────────────────────────────────────
# 动态间隔配置
# ──────────────────────────────────────────────────────────────────────

DEFAULT_INTERVALS = {
    "Bloomberg Economics": 300,
    "Bloomberg Markets": 300,
    "WSJ Economy": 300,
    "WSJ Markets": 300,
    "CNBC Technology": 300,
    "Reuters-Business": 300,
    "MarketWatch-Top": 300,
    "Yahoo Finance-News": 300,
    "Politico Politics": 300,
    "WhiteHouse Exec Orders": 900,
    "Fed Speeches": 900,
    "Fed Press Releases": 900,
    "CFTC Press Releases": 900,
    "Trump Truth Social": 300,
    "华尔街见闻-A 股": 180,
    "上交所 - 信息披露": 300,
    "深交所 - 上市公告": 300,
}

MIN_INTERVAL = 30
MAX_INTERVAL = 1800
EMPTY_THRESHOLD = 10

def _get_redis_key(feed_name: str) -> str:
    return f"lucidpanda:feed_state:{feed_name}"

def _get_feed_state(feed_name: str) -> dict[str, Any]:
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = _get_redis_key(feed_name)
    state = r.hgetall(key)
    
    if not state:
        default_interval = DEFAULT_INTERVALS.get(feed_name, 120)
        state = {
            'current_interval': default_interval,
            'consecutive_empty_count': 0,
            'total_fetches': 0,
            'total_new_items': 0,
            'last_fetch_at': '',
            'last_new_item_at': '',
        }
    
    state['current_interval'] = int(state.get('current_interval', 120))
    state['consecutive_empty_count'] = int(state.get('consecutive_empty_count', 0))
    state['total_fetches'] = int(state.get('total_fetches', 0))
    state['total_new_items'] = int(state.get('total_new_items', 0))
    return state

def _update_feed_state(feed_name: str, state: dict[str, Any], new_items: int):
    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
    key = _get_redis_key(feed_name)
    now = datetime.utcnow().isoformat()
    
    state['total_fetches'] += 1
    state['last_fetch_at'] = now
    
    if new_items > 0:
        state['consecutive_empty_count'] = 0
        state['total_new_items'] += new_items
        state['last_new_item_at'] = now
    else:
        state['consecutive_empty_count'] += 1
    
    old_interval = state['current_interval']
    new_interval = old_interval
    
    if new_items == 0:
        if state['consecutive_empty_count'] >= EMPTY_THRESHOLD:
            new_interval = min(old_interval * 2, MAX_INTERVAL)
            if new_interval != old_interval:
                logger.info(f"📈 [{feed_name}] 连续{state['consecutive_empty_count']}次空，间隔调整为{new_interval}s")
    else:
        state['consecutive_empty_count'] = 0
        new_interval = max(old_interval // 2, MIN_INTERVAL)
        if new_interval != old_interval:
            logger.info(f"📉 [{feed_name}] 采集到{new_items}条，间隔调整为{new_interval}s")
    
    state['current_interval'] = new_interval
    
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
    state = _get_feed_state(feed_name)
    last_fetch = state.get('last_fetch_at', '')
    current_interval = state['current_interval']
    
    if not last_fetch:
        return True, current_interval
    
    try:
        last_fetch_dt = datetime.fromisoformat(last_fetch)
        elapsed = (datetime.utcnow() - last_fetch_dt).total_seconds()
        if elapsed < current_interval:
            remaining = current_interval - elapsed
            logger.debug(f"⏭️ [{feed_name}] 跳过 (剩余{remaining:.0f}s)")
            return False, current_interval
    except Exception as e:
        logger.warning(f"⚠️ [{feed_name}] 解析时间失败：{e}")
    
    return True, current_interval


# 注意：现在变为了强大的纯粹 async 函数！没有恶心的 asyncio.run() 包裹了！
@broker.task(max_retries=3)
async def fetch_single_feed_task(feed_name: str, feed_url: str, category: str) -> dict[str, Any]:
    db = IntelligenceDB()

    try:
        should_fetch, current_interval = _should_fetch(feed_name)
        if not should_fetch:
            return {'feed_name': feed_name, 'skipped': True, 'saved': 0}

        source = RSSHubSource(db=db)
        if source._semaphore is None:
            source._semaphore = asyncio.Semaphore(8)

        _DEFAULT_HEADERS = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=True) as client, \
                   httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=False) as ssl_client:
            config = {"name": feed_name, "url": feed_url, "category": category}
            # 原生的 await，快如闪电！
            items, _ = await source._fetch_feed_async(client, ssl_client, config)

        state = _get_feed_state(feed_name)

        saved = 0
        if items:
            try:
                # 数据库入库是同步的，使用 to_thread 防止阻塞事件循环
                saved = await asyncio.to_thread(db.batch_save_raw_intelligence, items)
            except Exception as e:
                logger.error(f"❌ [{feed_name}] 批量入库失败: {e}")
            
            if saved > 0:
                try:
                    r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                    r.publish('intelligence_updates', json.dumps({"type": "new_data", "count": saved}))
                    r.publish('lucidpanda:new_intelligence', json.dumps({"type": "new_data", "count": saved}))
                    logger.info(f"📣 [{feed_name}] 发布 Redis 唤醒事件")
                except Exception:
                    pass
        
        # 将 Redis 存储使用 asyncio.to_thread 处理
        await asyncio.to_thread(_update_feed_state, feed_name, state, saved)
        
        if saved > 0:
            logger.info(f"✅ [{feed_name}] 采集成功：{saved}条新情报")
            
        return {'feed_name': feed_name, 'skipped': False, 'saved': saved}
        
    except Exception as e:
        logger.error(f"❌ [{feed_name}] 采集失败：{e}")
        raise e

@broker.task(max_retries=2)
async def fetch_email_task() -> dict[str, Any]:
    """官方新闻邮件摄入任务"""
    from src.lucidpanda.core.di_container import EngineDependencies
    deps = EngineDependencies()
    db = deps.db
    email_source = deps.email_source
    
    try:
        items = await email_source.fetch_async()
        saved = 0
        if items:
            saved = await asyncio.to_thread(db.batch_save_raw_intelligence, items)
            if saved > 0:
                r = redis.from_url(settings.REDIS_URL, decode_responses=True)
                r.publish('lucidpanda:new_intelligence', json.dumps({"type": "new_data", "count": saved}))
                logger.info(f"✅ Email 摄入成功：{saved}条新情报")
        
        return {'source': 'Email', 'saved': saved}
    except Exception as e:
        logger.error(f"❌ Email 摄入失败：{e}")
        return {'source': 'Email', 'error': str(e)}


# 每分钟运行一次！通过给定时器加 schedule 标签实现
@broker.task(schedule=[{"cron": "* * * * *"}])
async def fetch_all_feeds() -> dict[str, Any]:
    logger.info("🔄 [TaskIQ] 开始执行全量信源采集检查 (原生并发协程)...")
    
    tasks = []
    for feed in TIER1_FEEDS_CONFIG:
        should_fetch, _ = _should_fetch(feed['name'])
        if should_fetch:
            tasks.append(await fetch_single_feed_task.kiq(feed['name'], feed['url'], feed['category']))
    
    # 2. Email Ingestion (每分钟检查一次官方邮件)
    tasks.append(await fetch_email_task.kiq())
    
    if not tasks:
        logger.info("📊 [TaskIQ] 所有信源未到时间，跳过本轮")
        return {'total_feeds': len(TIER1_FEEDS_CONFIG), 'fetched': 0}
        
    # TaskIQ 返回的是 TaskiqResult 对象。我们可以等待获取结果！
    logger.info(f"🚀 [TaskIQ] 已派发 {len(tasks)} 个采集任务到高速队列！")
    
    # 因为 TaskIQ 具有高度解耦特性，父任务只需把子任务送达即可！
    return {
        'total_feeds': len(TIER1_FEEDS_CONFIG),
        'dispatched': len(tasks)
    }
