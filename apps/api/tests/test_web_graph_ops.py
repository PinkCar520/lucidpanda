from src.lucidpanda.utils.web_graph_ops import (
    FusedCacheStore,
    build_graph_quality_alerts,
    fused_cache_key,
)


class _FakeRedis:
    def __init__(self):
        self.kv = {}
        self.sets = {}

    def get(self, key):
        return self.kv.get(key)

    def setex(self, key, _ttl, value):
        self.kv[key] = value
        return True

    def sadd(self, key, value):
        bucket = self.sets.setdefault(key, set())
        bucket.add(value)
        return 1

    def smembers(self, key):
        return self.sets.get(key, set())

    def delete(self, *keys):
        removed = 0
        for key in keys:
            if key in self.kv:
                del self.kv[key]
                removed += 1
            if key in self.sets:
                del self.sets[key]
                removed += 1
        return removed

    def expire(self, _key, _ttl):
        return 1


def test_fused_cache_key_changes_with_cursor():
    key_a = fused_cache_key(limit=30, before_timestamp=None)
    key_b = fused_cache_key(limit=30, before_timestamp="2026-03-09T12:00:00Z")
    assert key_a != key_b


def test_fused_cache_store_local_roundtrip():
    store = FusedCacheStore(
        ttl_seconds=30,
        namespace="test:fused",
        redis_client_getter=lambda: None,
    )
    payload = {"data": [1], "count": 1}
    store.set(limit=30, before_timestamp=None, payload=payload)
    assert store.get(limit=30, before_timestamp=None) == payload


def test_fused_cache_store_reads_redis_when_local_miss():
    fake_redis = _FakeRedis()
    store = FusedCacheStore(
        ttl_seconds=30,
        namespace="test:fused",
        redis_client_getter=lambda: fake_redis,
    )
    payload = {"data": [{"id": 1}], "count": 1}
    store.set(limit=20, before_timestamp="2026-03-09T00:00:00Z", payload=payload)
    store._local_cache.clear()
    assert store.get(limit=20, before_timestamp="2026-03-09T00:00:00Z") == payload


def test_invalidate_fused_cache_clears_local_and_redis():
    fake_redis = _FakeRedis()
    store = FusedCacheStore(
        ttl_seconds=30,
        namespace="test:fused",
        redis_client_getter=lambda: fake_redis,
    )
    store.set(limit=10, before_timestamp=None, payload={"data": []})
    removed = store.invalidate()
    assert removed["local_removed"] >= 1
    assert removed["redis_removed"] >= 1
    assert store._local_cache == {}


def test_build_graph_quality_alerts_flags_risks():
    alerts = build_graph_quality_alerts(
        coverage_pct=45.0,
        in_vocab_pct=52.0,
        valid_direction_pct=80.0,
        malformed_pct=28.0,
        coverage_threshold=60.0,
        in_vocab_threshold=70.0,
        direction_threshold=90.0,
        malformed_threshold=20.0,
    )
    assert {item["metric"] for item in alerts} == {
        "relation_coverage_pct",
        "in_vocab_pct",
        "valid_direction_pct",
        "malformed_pct",
    }


def test_build_graph_quality_alerts_empty_when_healthy():
    alerts = build_graph_quality_alerts(
        coverage_pct=75.0,
        in_vocab_pct=80.0,
        valid_direction_pct=98.0,
        malformed_pct=5.0,
        coverage_threshold=60.0,
        in_vocab_threshold=70.0,
        direction_threshold=90.0,
        malformed_threshold=20.0,
    )
    assert alerts == []
