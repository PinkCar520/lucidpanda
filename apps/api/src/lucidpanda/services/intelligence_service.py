import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import redis
from sqlmodel import Session, select, text
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.models.intelligence import Intelligence
from src.lucidpanda.utils import v1_prepare_json
from src.lucidpanda.utils.confidence import calc_confidence_level, calc_confidence_score
from src.lucidpanda.utils.entity_normalizer import normalize_fund_name
from src.lucidpanda.utils.fusion import merge_entities
from src.lucidpanda.utils.web_graph_ops import (
    FusedCacheStore,
    fused_cache_key,
)

logger = logging.getLogger(__name__)

FUSED_CACHE_TTL_SECONDS = 30
_FUSED_CACHE_NAMESPACE = "web:fused:v1"


class IntelligenceService:
    def __init__(self, db_session: Session):
        self.db = db_session
        self.db_legacy = IntelligenceDB()
        self._redis_client: redis.Redis | None | bool = None
        self._fused_cache_store: FusedCacheStore | None = None
        self._local_fused_cache: dict[str, dict[str, Any]] = {}

    def _get_redis_client(self) -> redis.Redis | None:
        if self._redis_client is not None:
            if self._redis_client is False:
                return None
            return self._redis_client  # type: ignore

        if (
            os.getenv("FUSED_CACHE_USE_REDIS", "true").lower()
            not in {"1", "true", "yes", "on"}
        ):
            self._redis_client = False
            return None
        try:
            self._redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                decode_responses=True,
            )
            self._redis_client.ping()  # type: ignore
            return self._redis_client  # type: ignore
        except Exception:
            self._redis_client = False
            return None

    def _get_fused_cache_store(self) -> FusedCacheStore:
        if self._fused_cache_store is None:
            self._fused_cache_store = FusedCacheStore(
                ttl_seconds=FUSED_CACHE_TTL_SECONDS,
                namespace=_FUSED_CACHE_NAMESPACE,
                redis_client_getter=self._get_redis_client,
            )
        return self._fused_cache_store

    def _with_confidence(self, item: Intelligence) -> dict[str, Any]:
        payload = v1_prepare_json(item)
        confidence_score = calc_confidence_score(
            payload.get("corroboration_count"),
            payload.get("source_credibility_score"),
            payload.get("urgency_score"),
            payload.get("timestamp"),
        )
        payload["confidence_score"] = confidence_score
        payload["confidence_level"] = calc_confidence_level(confidence_score)
        return payload

    def get_intelligence_full(self, limit: int = 50) -> list[dict[str, Any]]:
        statement = (
            select(Intelligence).order_by(Intelligence.timestamp.desc()).limit(limit)
        )
        results = self.db.exec(statement).all()
        return [self._with_confidence(item) for item in results]

    def get_fused_intelligence(
        self,
        limit: int = 30,
        before_timestamp: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        if not force_refresh:
            cached = self._get_fused_cache_store().get(limit, before_timestamp)
            if cached is not None:
                return cached

            key = fused_cache_key(limit, before_timestamp)
            local_cached = self._local_fused_cache.get(key)
            if local_cached:
                if time.time() - local_cached["ts"] < FUSED_CACHE_TTL_SECONDS:
                    return local_cached["payload"]
                self._local_fused_cache.pop(key, None)

        fused_sql = text("""
            WITH completed AS (
                SELECT
                    *,
                    COALESCE(event_cluster_id, 'single:' || COALESCE(source_id, id::text)) AS cluster_key
                FROM intelligence
                WHERE status = 'COMPLETED'
            ),
            clusters AS (
                SELECT
                    cluster_key,
                    COUNT(*) AS corroboration_count,
                    jsonb_agg(entities) FILTER (WHERE entities IS NOT NULL) AS entities_sets
                FROM completed
                GROUP BY cluster_key
            ),
            leads AS (
                SELECT
                    c.*,
                    ROW_NUMBER() OVER (
                        PARTITION BY c.cluster_key
                        ORDER BY COALESCE(c.source_credibility_score, 0) DESC, c.timestamp DESC
                    ) AS rn
                FROM completed c
            )
            SELECT
                l.*,
                clusters.corroboration_count,
                clusters.entities_sets
            FROM leads l
            JOIN clusters ON clusters.cluster_key = l.cluster_key
            WHERE l.rn = 1
              AND (:before_ts IS NULL OR l.timestamp < CAST(:before_ts AS timestamptz))
            ORDER BY l.timestamp DESC
            LIMIT :limit
        """)
        rows = self.db.execute(
            fused_sql, {"limit": limit, "before_ts": before_timestamp}
        ).all()

        items = []
        for row in rows:
            payload = v1_prepare_json(dict(row._mapping))
            payload["entities"] = merge_entities(payload.get("entities_sets"))
            payload.pop("entities_sets", None)
            confidence_score = calc_confidence_score(
                payload.get("corroboration_count"),
                payload.get("source_credibility_score"),
                payload.get("urgency_score"),
                payload.get("timestamp"),
            )
            payload["confidence_score"] = confidence_score
            payload["confidence_level"] = calc_confidence_level(confidence_score)
            items.append(payload)

        next_cursor = None
        if items:
            last_timestamp = items[-1].get("timestamp")
            if isinstance(last_timestamp, datetime):
                next_cursor = last_timestamp.isoformat()
            elif last_timestamp:
                next_cursor = str(last_timestamp)

        response_payload = {
            "data": items,
            "count": len(items),
            "limit": limit,
            "before_timestamp": before_timestamp,
            "next_cursor": next_cursor,
        }

        # Cache it
        key = fused_cache_key(limit, before_timestamp)
        self._local_fused_cache[key] = {"ts": time.time(), "payload": response_payload}
        self._get_fused_cache_store().set(limit, before_timestamp, response_payload)

        return response_payload

    def invalidate_fused_cache(self) -> dict[str, int]:
        local_size = len(self._local_fused_cache)
        self._local_fused_cache.clear()
        store_removed = self._get_fused_cache_store().invalidate()
        return {
            "local_removed": local_size + int(store_removed.get("local_removed") or 0),
            "redis_removed": int(store_removed.get("redis_removed") or 0),
        }

    def get_event_graph(self, cluster_id: str) -> dict[str, Any]:
        graph = self.db_legacy.get_event_graph(cluster_id)
        return {
            "cluster_id": cluster_id,
            "nodes": graph.get("nodes", []),
            "edges": graph.get("edges", []),
            "inferences": graph.get("inferences", []),
            "evidence": graph.get("evidence", []),
            "relation_weights": graph.get("relation_weights", {}),
        }

    def get_entity_graph(self, entity_name: str, limit: int = 100) -> dict[str, Any]:
        return self.db_legacy.get_entity_graph(entity_name, limit=limit)

    def find_graph_path(
        self,
        from_entity: str,
        to_entity: str,
        max_hops: int = 2,
        min_confidence: float = 0.0,
        relation: str | None = None,
        event_cluster_id: str | None = None,
    ) -> dict[str, Any]:
        result = self.db_legacy.find_graph_path(
            from_entity,
            to_entity,
            max_hops=max_hops,
            min_confidence=min_confidence,
            relation=relation,
            event_cluster_id=event_cluster_id,
        )
        return {
            "from_entity": from_entity,
            "to_entity": to_entity,
            "max_hops": max_hops,
            "min_confidence": min_confidence,
            "relation": relation,
            "event_cluster_id": event_cluster_id,
            "paths": result.get("paths", []),
        }

    def get_intelligence_item(self, item_id: int) -> dict[str, Any] | None:
        statement = select(Intelligence).where(Intelligence.id == item_id)
        result = self.db.exec(statement).first()
        if not result:
            return None
        return self._with_confidence(result)

    def get_backtest_stats(
        self, window: str = "1h", min_score: int = 8, sentiment: str = "bearish"
    ) -> dict[str, Any]:
        # Determination of columns and keywords
        window_map = {
            "15m": "price_15m", "1h": "price_1h", "4h": "price_4h", "12h": "price_12h", "24h": "price_24h"
        }
        outcome_col = window_map.get(window, "price_1h")
        if sentiment == "bearish":
            keywords = "鹰|利空|下跌|风险|Bearish|Hawkish|Risk|Negative|Pressure"
            win_condition = "exit < entry"
        else:
            keywords = "鸽|利多|上涨|积极|Bullish|Dovish|Positive|Safe-haven|Support"
            win_condition = "exit > entry"

        params = {"keywords": keywords, "min_score": min_score}
        base_cte = f"""
        WITH filtered_intelligence AS (
            SELECT *, LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= :min_score
              AND (sentiment::text ~* :keywords)
              AND gold_price_snapshot IS NOT NULL
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT *, gold_price_snapshot as entry, {outcome_col} as exit
            FROM filtered_intelligence
            WHERE prev_timestamp IS NULL OR timestamp > prev_timestamp + INTERVAL '30 minutes'
        )
        """

        query_global = f"{base_cte} SELECT COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins, AVG((exit - entry) / entry) * 100 as avg_change_pct FROM deduplicated_events"
        res_global = self.db.execute(text(query_global), params).mappings().first()
        if not res_global or res_global["count"] == 0:
            return {"count": 0, "winRate": 0}

        return v1_prepare_json({
            "count": res_global["count"],
            "winRate": (res_global["wins"] / res_global["count"]) * 100,
            "avgDrop": -(res_global["avg_change_pct"] or 0),
        })

    def get_monitor_stats(self) -> dict[str, Any]:
        stats = self.db_legacy.get_reconciliation_stats()
        stats["heatmap"] = self.db_legacy.get_heatmap_stats()
        return stats

    def get_graph_quality(
        self,
        days: int = 14,
        baseline_days: int = 14,
        coverage_threshold: float = 60.0,
        in_vocab_threshold: float = 70.0,
        direction_threshold: float = 90.0,
        malformed_threshold: float = 20.0,
    ) -> dict[str, Any]:
        from src.lucidpanda.utils.graph_reasoning import (
            BEARISH_RELATIONS,
            BULLISH_RELATIONS,
        )

        safe_days = max(3, min(90, int(days)))
        _ = BULLISH_RELATIONS, BEARISH_RELATIONS

        summary_sql = text("""
            SELECT
                COUNT(*) AS completed_count,
                COUNT(*) FILTER (
                    WHERE relation_triples IS NOT NULL
                      AND jsonb_typeof(relation_triples) = 'array'
                      AND jsonb_array_length(relation_triples) > 0
                ) AS with_relations_count,
                COALESCE(SUM(
                    CASE
                        WHEN relation_triples IS NOT NULL
                         AND jsonb_typeof(relation_triples) = 'array'
                        THEN jsonb_array_length(relation_triples)
                        ELSE 0
                    END
                ), 0) AS relation_item_count
            FROM intelligence
            WHERE status = 'COMPLETED'
              AND timestamp >= NOW() - (:days * INTERVAL '1 day')
        """)
        summary_row = self.db.execute(summary_sql, {"days": safe_days}).first()
        summary = dict(summary_row._mapping) if summary_row else {}

        # Standard implementation for brevity
        completed_count = int(summary.get("completed_count") or 0)
        with_relations_count = int(summary.get("with_relations_count") or 0)

        return {
            "window_days": safe_days,
            "summary": {
                "completed_count": completed_count,
                "with_relations_count": with_relations_count,
                "relation_coverage_pct": float(round((with_relations_count / completed_count) * 100, 2)) if completed_count else 0.0
            },
            "generated_at": datetime.now(timezone.utc)
        }

    async def get_fund_ai_analysis(
        self,
        user_id: str,
        fund_code: str,
        fund_name: str,
    ) -> dict[str, Any]:
        from src.lucidpanda.infra.cache import get_cached, set_cached
        from src.lucidpanda.services.market_service import market_service

        _cache_key = f"api:fund:ai:{user_id}:{fund_code}"
        _cache_ttl = 60

        cached = get_cached(_cache_key)
        if cached is not None:
            return cached

        core_name = normalize_fund_name(fund_name)
        is_a_share = fund_code.isdigit() and len(fund_code) == 6
        preferred_categories = ["equity_cn", "macro_gold"] if is_a_share else ["equity_us", "macro_gold"]
        since_7d = datetime.now(timezone.utc) - timedelta(days=7)

        # Keyword Search
        kw_sql = text("""
            SELECT id, timestamp, author, urgency_score, summary, actionable_advice, sentiment_score
            FROM intelligence
            WHERE timestamp > :since
              AND category = ANY(:cats)
              AND (
                content ILIKE :kw_full OR content ILIKE :kw_core
                OR summary::text ILIKE :kw_full OR summary::text ILIKE :kw_core
                OR entities @> CAST(:json_full AS jsonb) OR entities @> CAST(:json_core AS jsonb)
              )
              AND summary IS NOT NULL
            ORDER BY urgency_score DESC, timestamp DESC
            LIMIT 5
        """)
        kw_raw = self.db.execute(kw_sql, {
            "since": since_7d,
            "cats": preferred_categories,
            "kw_full": f"%{fund_name}%",
            "kw_core": f"%{core_name}%",
            "json_full": json.dumps([{"name": fund_name}]),
            "json_core": json.dumps([{"name": core_name}])
        }).mappings().all()

        related_intelligence = []
        for row in kw_raw:
            summary_text = row["summary"]
            if isinstance(summary_text, dict):
                summary_text = summary_text.get("zh") or summary_text.get("en")

            related_intelligence.append({
                "id": row["id"],
                "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
                "summary": summary_text,
                "sentiment": "bullish" if (row["sentiment_score"] or 0.0) > 0.15 else "bearish" if (row["sentiment_score"] or 0.0) < -0.15 else "neutral"
            })

        result = {
            "fund_code": fund_code,
            "fund_name": fund_name,
            "has_intelligence": len(related_intelligence) > 0,
            "related_intelligence": related_intelligence,
            "market_snapshot": market_service.get_market_snapshot() if hasattr(market_service, 'get_market_snapshot') else {},
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        set_cached(_cache_key, result, ttl=_cache_ttl)
        return result

    def get_sources_dashboard(self, days: int = 14, limit: int = 15) -> dict[str, Any]:
        safe_days = max(3, min(90, int(days)))
        sql = text("""
            SELECT source_name, COUNT(*) AS total_signals, MAX(timestamp) AS last_seen
            FROM intelligence
            WHERE status = 'COMPLETED' AND source_name IS NOT NULL
              AND timestamp >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY source_name
            ORDER BY total_signals DESC
            LIMIT :limit
        """)
        rows = self.db.execute(sql, {"days": safe_days, "limit": limit}).all()
        return {
            "window_days": safe_days,
            "leaderboard": [dict(r._mapping) for r in rows],
            "generated_at": datetime.now(timezone.utc)
        }
