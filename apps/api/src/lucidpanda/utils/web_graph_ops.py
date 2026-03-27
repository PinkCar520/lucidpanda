from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any, cast


def fused_cache_key(limit: int, before_timestamp: str | None) -> str:
    return json.dumps({"limit": limit, "before_timestamp": before_timestamp}, sort_keys=True)


class FusedCacheStore:
    def __init__(
        self,
        ttl_seconds: int,
        namespace: str,
        redis_client_getter: Callable[[], Any | None],
    ):
        self.ttl_seconds = int(ttl_seconds)
        self.namespace = namespace
        self._redis_client_getter = redis_client_getter
        self._local_cache: dict[str, dict[str, Any]] = {}

    def _redis_key(self, limit: int, before_timestamp: str | None) -> str:
        return f"{self.namespace}:{fused_cache_key(limit, before_timestamp)}"

    def get(self, limit: int, before_timestamp: str | None) -> dict[str, Any] | None:
        redis_client = self._redis_client_getter()
        if redis_client:
            try:
                raw = redis_client.get(self._redis_key(limit, before_timestamp))
                if raw:
                    return cast(dict[str, Any], json.loads(raw))
            except Exception:
                pass

        key = fused_cache_key(limit, before_timestamp)
        cached = self._local_cache.get(key)
        if not cached:
            return None
        if time.time() - cached["ts"] > self.ttl_seconds:
            self._local_cache.pop(key, None)
            return None
        return cast(dict[str, Any], cached["payload"])

    def set(self, limit: int, before_timestamp: str | None, payload: dict[str, Any]) -> None:
        key = fused_cache_key(limit, before_timestamp)
        self._local_cache[key] = {"ts": time.time(), "payload": payload}

        redis_client = self._redis_client_getter()
        if redis_client:
            try:
                redis_key = self._redis_key(limit, before_timestamp)
                redis_client.setex(redis_key, self.ttl_seconds, json.dumps(payload, default=str))
                keyset = f"{self.namespace}:keys"
                redis_client.sadd(keyset, redis_key)
                redis_client.expire(keyset, max(self.ttl_seconds * 5, 180))
            except Exception:
                pass

    def invalidate(self) -> dict[str, int]:
        local_removed = len(self._local_cache)
        self._local_cache.clear()
        redis_removed = 0

        redis_client = self._redis_client_getter()
        if redis_client:
            try:
                keyset = f"{self.namespace}:keys"
                cache_keys = list(redis_client.smembers(keyset))
                if cache_keys:
                    redis_removed += int(redis_client.delete(*cache_keys) or 0)
                redis_removed += int(redis_client.delete(keyset) or 0)
            except Exception:
                pass

        return {"local_removed": local_removed, "redis_removed": redis_removed}


def build_graph_quality_alerts(
    coverage_pct: float,
    in_vocab_pct: float,
    valid_direction_pct: float,
    malformed_pct: float,
    coverage_threshold: float,
    in_vocab_threshold: float,
    direction_threshold: float,
    malformed_threshold: float,
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    if coverage_pct < coverage_threshold:
        alerts.append({
            "metric": "relation_coverage_pct",
            "severity": "warning",
            "value": coverage_pct,
            "threshold": coverage_threshold,
            "message": f"coverage below threshold: {coverage_pct} < {coverage_threshold}",
        })
    if in_vocab_pct < in_vocab_threshold:
        alerts.append({
            "metric": "in_vocab_pct",
            "severity": "warning",
            "value": in_vocab_pct,
            "threshold": in_vocab_threshold,
            "message": f"in-vocab below threshold: {in_vocab_pct} < {in_vocab_threshold}",
        })
    if valid_direction_pct < direction_threshold:
        alerts.append({
            "metric": "valid_direction_pct",
            "severity": "critical",
            "value": valid_direction_pct,
            "threshold": direction_threshold,
            "message": f"direction-valid below threshold: {valid_direction_pct} < {direction_threshold}",
        })
    if malformed_pct > malformed_threshold:
        alerts.append({
            "metric": "malformed_pct",
            "severity": "critical",
            "value": malformed_pct,
            "threshold": malformed_threshold,
            "message": f"malformed above threshold: {malformed_pct} > {malformed_threshold}",
        })
    return alerts
