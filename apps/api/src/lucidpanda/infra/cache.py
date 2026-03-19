"""
轻量级 Redis 缓存工具 — 供 API 层使用（同步，带降级）

用法：
    from src.lucidpanda.infra.cache import get_cached, set_cached

    data = get_cached("pulse:global")
    if data is None:
        data = compute_expensive_thing()
        set_cached("pulse:global", data, ttl=30)
"""
import json
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_redis_client = None


def _get_client():
    """懒加载单例 Redis 客户端（同步）。连接失败时静默返回 None。"""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    try:
        import redis as redis_lib
        from src.lucidpanda.config import settings
        _redis_client = redis_lib.from_url(
            settings.REDIS_URL,
            decode_responses=True,
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        # 简单 ping 确认可用
        _redis_client.ping()
        logger.debug("✅ Redis cache client ready")
    except Exception as e:
        logger.warning(f"⚠️ Redis unavailable, cache disabled: {e}")
        _redis_client = None
    return _redis_client


def get_cached(key: str) -> Optional[Any]:
    """从 Redis 读取缓存，反序列化为 Python 对象。不可用时返回 None。"""
    try:
        client = _get_client()
        if client is None:
            return None
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"Cache GET miss/error [{key}]: {e}")
        return None


def set_cached(key: str, value: Any, ttl: int = 30) -> None:
    """将 Python 对象序列化后写入 Redis，ttl 单位为秒。失败时静默忽略。"""
    try:
        client = _get_client()
        if client is None:
            return
        client.setex(key, ttl, json.dumps(value, default=str))
    except Exception as e:
        logger.debug(f"Cache SET error [{key}]: {e}")


def invalidate(key: str) -> None:
    """删除指定缓存 key。"""
    try:
        client = _get_client()
        if client:
            client.delete(key)
    except Exception:
        pass
