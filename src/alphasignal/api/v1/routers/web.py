from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlmodel import Session, select, text
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import time
import os
import redis
import logging
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.fund import FundMetadata, FundValuationArchive
from src.alphasignal.models.intelligence import Intelligence
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.core.fund_engine import FundEngine
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.utils import v1_prepare_json
from src.alphasignal.utils.confidence import calc_confidence_score, calc_confidence_level
from src.alphasignal.utils.fusion import merge_entities
from src.alphasignal.utils.graph_reasoning import BULLISH_RELATIONS, BEARISH_RELATIONS
from src.alphasignal.utils.web_graph_ops import (
    FusedCacheStore,
    build_graph_quality_alerts,
    fused_cache_key,
)

router = APIRouter()
FUSED_CACHE_TTL_SECONDS = 30
_fused_cache: dict[str, dict[str, Any]] = {}
_redis_client = None
_FUSED_CACHE_NAMESPACE = "web:fused:v1"
_fused_cache_store = None


def _with_confidence(item: Intelligence) -> Dict[str, Any]:
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


def _fused_cache_key(limit: int, before_timestamp: Optional[str]) -> str:
    return fused_cache_key(limit, before_timestamp)


def _get_fused_redis_client():
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if os.getenv("FUSED_CACHE_USE_REDIS", "true").lower() not in {"1", "true", "yes", "on"}:
        _redis_client = False
        return None
    try:
        _redis_client = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)
        _redis_client.ping()
        return _redis_client
    except Exception:
        _redis_client = False
        return None


def _fused_cache_redis_key(limit: int, before_timestamp: Optional[str]) -> str:
    return f"{_FUSED_CACHE_NAMESPACE}:{_fused_cache_key(limit, before_timestamp)}"


def _get_fused_cache_store() -> FusedCacheStore:
    global _fused_cache_store
    if _fused_cache_store is None:
        _fused_cache_store = FusedCacheStore(
            ttl_seconds=FUSED_CACHE_TTL_SECONDS,
            namespace=_FUSED_CACHE_NAMESPACE,
            redis_client_getter=_get_fused_redis_client,
        )
    return _fused_cache_store


def _get_fused_cache(limit: int, before_timestamp: Optional[str]) -> Optional[Dict[str, Any]]:
    cached = _get_fused_cache_store().get(limit, before_timestamp)
    if cached is not None:
        return cached
    key = _fused_cache_key(limit, before_timestamp)
    local_cached = _fused_cache.get(key)
    if not local_cached:
        return None
    if time.time() - local_cached["ts"] > FUSED_CACHE_TTL_SECONDS:
        _fused_cache.pop(key, None)
        return None
    return local_cached["payload"]


def _set_fused_cache(limit: int, before_timestamp: Optional[str], payload: Dict[str, Any]) -> None:
    key = _fused_cache_key(limit, before_timestamp)
    _fused_cache[key] = {"ts": time.time(), "payload": payload}
    _get_fused_cache_store().set(limit, before_timestamp, payload)


def _invalidate_fused_cache() -> Dict[str, int]:
    local_size = len(_fused_cache)
    _fused_cache.clear()
    store_removed = _get_fused_cache_store().invalidate()
    return {
        "local_removed": local_size + int(store_removed.get("local_removed") or 0),
        "redis_removed": int(store_removed.get("redis_removed") or 0),
    }

@router.get("/watchlist", response_model=Dict[str, Any])
async def get_web_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get user's watchlist for Web.
    Maintains the {"data": [...]} wrapper for TanStack Query compatibility.
    """
    db_legacy = IntelligenceDB()
    rows = db_legacy.get_watchlist(str(current_user.id))
    return v1_prepare_json({"data": [{"code": r['fund_code'], "name": r['fund_name']} for r in rows]})

@router.get("/funds/batch-valuation", response_model=Dict[str, Any])
async def get_web_batch_valuations(
    codes: str, 
    mode: str = "full",
    current_user: User = Depends(get_current_user)
):
    """
    Batch valuation for Web with full data density.
    """
    if not codes:
        return {"data": []}
    
    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    engine = FundEngine()
    
    results = engine.calculate_batch_valuation(code_list, summary=(mode == "summary"))
    
    # Enrich with stats
    db_legacy = IntelligenceDB()
    stats_map = db_legacy.get_fund_stats(code_list)
    
    for res in results:
        f_code = res.get('fund_code')
        if f_code in stats_map:
            res['stats'] = stats_map[f_code]
            
    return v1_prepare_json({"data": results})

@router.get("/funds/{code}/valuation", response_model=Dict[str, Any])
async def get_web_fund_valuation(code: str, current_user: User = Depends(get_current_user)):
    """
    Detailed single fund valuation for Web.
    """
    engine = FundEngine()
    results = engine.calculate_batch_valuation([code])
    if results:
        db_legacy = IntelligenceDB()
        stats_map = db_legacy.get_fund_stats([code])
        if code in stats_map:
            results[0]['stats'] = stats_map[code]
        return v1_prepare_json(results[0])
    return {"error": "Valuation failed"}

@router.get("/funds/{code}/history", response_model=Dict[str, Any])
async def get_web_fund_history(code: str, limit: int = 30, current_user: User = Depends(get_current_user)):
    """
    Historical performance for Web.
    """
    db_legacy = IntelligenceDB()
    history = db_legacy.get_valuation_history(code, limit)
    
    formatted_history = []
    for h in history:
        item = dict(h)
        if 'trade_date' in item and hasattr(item['trade_date'], 'isoformat'):
            item['trade_date'] = item['trade_date'].isoformat()
        formatted_history.append(item)
    return v1_prepare_json({"data": formatted_history})

@router.get("/intelligence/full", response_model=Dict[str, Any])
async def get_web_intelligence_full(
    limit: int = 50,
    db: Session = Depends(get_session)
):
    """
    Returns full rich JSONB objects for Web localized rendering.
    """
    statement = select(Intelligence).order_by(Intelligence.timestamp.desc()).limit(limit)
    results = db.exec(statement).all()
    return {"data": [_with_confidence(item) for item in results]}

from pydantic import BaseModel

class WatchlistItemDTO(BaseModel):
    code: str
    name: str

@router.post("/watchlist", response_model=Dict[str, Any])
async def add_web_watchlist(
    item: WatchlistItemDTO,
    current_user: User = Depends(get_current_user)
):
    """Add a fund to watchlist via Web BFF."""
    db_legacy = IntelligenceDB()
    success = db_legacy.add_to_watchlist(item.code, item.name, str(current_user.id))
    return {"success": success}

@router.delete("/watchlist/{code}", response_model=Dict[str, Any])
async def remove_web_watchlist(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Remove a fund from watchlist via Web BFF."""
    db_legacy = IntelligenceDB()
    success = db_legacy.remove_from_watchlist(code, str(current_user.id))
    return {"success": success}

@router.get("/intelligence/fused", response_model=Dict[str, Any])
async def get_web_fused_intelligence(
    limit: int = 30,
    before_timestamp: Optional[str] = None,
    force_refresh: bool = False,
    db: Session = Depends(get_session)
):
    """
    Fused intelligence view（NIE-like）:
    - 每个事件 cluster 输出 1 条 lead 记录
    - 聚合 corroboration_count / confidence
    - 合并 cluster entities
    """
    cached_payload = _get_fused_cache(limit, before_timestamp)
    if cached_payload is not None and not force_refresh:
        return cached_payload

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
    rows = db.execute(fused_sql, {"limit": limit, "before_ts": before_timestamp}).all()

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
    _set_fused_cache(limit, before_timestamp, response_payload)
    return response_payload


@router.post("/intelligence/fused/cache/invalidate", response_model=Dict[str, Any])
async def invalidate_web_fused_cache(current_user: User = Depends(get_current_user)):
    del current_user
    removed = _invalidate_fused_cache()
    return v1_prepare_json({
        "success": True,
        "removed": removed,
        "invalidated_at": datetime.utcnow(),
    })


@router.get("/graph/event/{cluster_id}", response_model=Dict[str, Any])
async def get_web_event_graph(cluster_id: str):
    """按事件 cluster 返回知识图谱。"""
    db_legacy = IntelligenceDB()
    graph = db_legacy.get_event_graph(cluster_id)
    return v1_prepare_json({
        "cluster_id": cluster_id,
        "nodes": graph.get("nodes", []),
        "edges": graph.get("edges", []),
        "inferences": graph.get("inferences", []),
        "evidence": graph.get("evidence", []),
        "relation_weights": graph.get("relation_weights", {}),
    })


@router.get("/graph/entity/{entity_name}", response_model=Dict[str, Any])
async def get_web_entity_graph(entity_name: str, limit: int = 100):
    """按实体返回邻接子图。"""
    db_legacy = IntelligenceDB()
    graph = db_legacy.get_entity_graph(entity_name, limit=limit)
    return v1_prepare_json(graph)


@router.get("/graph/path", response_model=Dict[str, Any])
async def get_web_graph_path(
    from_entity: str,
    to_entity: str,
    max_hops: int = 2,
    min_confidence: float = 0.0,
    relation: Optional[str] = None,
    event_cluster_id: Optional[str] = None,
):
    """查找两个实体之间的1~2跳路径。"""
    db_legacy = IntelligenceDB()
    result = db_legacy.find_graph_path(
        from_entity,
        to_entity,
        max_hops=max_hops,
        min_confidence=min_confidence,
        relation=relation,
        event_cluster_id=event_cluster_id,
    )
    return v1_prepare_json({
        "from_entity": from_entity,
        "to_entity": to_entity,
        "max_hops": max_hops,
        "min_confidence": min_confidence,
        "relation": relation,
        "event_cluster_id": event_cluster_id,
        "paths": result.get("paths", []),
    })


@router.get("/graph/quality", response_model=Dict[str, Any])
async def get_web_graph_quality(
    days: int = 14,
    baseline_days: int = 14,
    coverage_threshold: float = 60.0,
    in_vocab_threshold: float = 70.0,
    direction_threshold: float = 90.0,
    malformed_threshold: float = 20.0,
    db: Session = Depends(get_session)
):
    """
    图谱抽取质量快照（用于 Phase 2 生产化观测）：
    - relations 覆盖率
    - 平均关系条数
    - 非法/不完整关系占比
    - 合法方向占比（forward/bidirectional）
    """
    safe_days = max(3, min(90, int(days)))
    allowed_relations = sorted(BULLISH_RELATIONS.union(BEARISH_RELATIONS))

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
    summary_row = db.execute(summary_sql, {"days": safe_days}).first()
    summary = dict(summary_row._mapping) if summary_row else {}

    relation_item_sql = text("""
        WITH rels AS (
            SELECT jsonb_array_elements(relation_triples) AS rel
            FROM intelligence
            WHERE status = 'COMPLETED'
              AND relation_triples IS NOT NULL
              AND jsonb_typeof(relation_triples) = 'array'
              AND timestamp >= NOW() - (:days * INTERVAL '1 day')
        )
        SELECT
            COUNT(*) AS total_items,
            COUNT(*) FILTER (
                WHERE COALESCE(NULLIF(TRIM(rel->>'predicate'), ''), NULLIF(TRIM(rel->>'relation'), '')) IS NULL
                   OR COALESCE(NULLIF(TRIM(rel->>'subject'), ''), NULLIF(TRIM(rel->>'from'), '')) IS NULL
                   OR COALESCE(NULLIF(TRIM(rel->>'object'), ''), NULLIF(TRIM(rel->>'to'), '')) IS NULL
            ) AS malformed_items,
            COUNT(*) FILTER (
                WHERE LOWER(COALESCE(rel->>'direction', 'forward')) IN ('forward', 'bidirectional')
            ) AS valid_direction_items,
            COUNT(*) FILTER (
                WHERE LOWER(COALESCE(NULLIF(TRIM(rel->>'predicate'), ''), NULLIF(TRIM(rel->>'relation'), ''))) = ANY(:allowed_relations)
            ) AS in_vocab_items
        FROM rels
    """)
    relation_row = db.execute(relation_item_sql, {"days": safe_days, "allowed_relations": allowed_relations}).first()
    relation_stats = dict(relation_row._mapping) if relation_row else {}

    completed_count = int(summary.get("completed_count") or 0)
    with_relations_count = int(summary.get("with_relations_count") or 0)
    relation_item_count = int(summary.get("relation_item_count") or 0)
    total_items = int(relation_stats.get("total_items") or 0)
    malformed_items = int(relation_stats.get("malformed_items") or 0)
    valid_direction_items = int(relation_stats.get("valid_direction_items") or 0)
    in_vocab_items = int(relation_stats.get("in_vocab_items") or 0)

    coverage_pct = round((with_relations_count / completed_count) * 100, 2) if completed_count else 0.0
    avg_relations_per_item = round((relation_item_count / with_relations_count), 3) if with_relations_count else 0.0
    malformed_pct = round((malformed_items / total_items) * 100, 2) if total_items else 0.0
    valid_direction_pct = round((valid_direction_items / total_items) * 100, 2) if total_items else 0.0
    in_vocab_pct = round((in_vocab_items / total_items) * 100, 2) if total_items else 0.0

    trend_sql = text("""
        WITH day_bucket AS (
            SELECT
                DATE_TRUNC('day', timestamp) AS day,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_count,
                COUNT(*) FILTER (
                    WHERE status = 'COMPLETED'
                      AND relation_triples IS NOT NULL
                      AND jsonb_typeof(relation_triples) = 'array'
                      AND jsonb_array_length(relation_triples) > 0
                ) AS with_relations_count,
                COALESCE(SUM(
                    CASE
                        WHEN status = 'COMPLETED'
                          AND relation_triples IS NOT NULL
                          AND jsonb_typeof(relation_triples) = 'array'
                        THEN jsonb_array_length(relation_triples)
                        ELSE 0
                    END
                ), 0) AS relation_item_count
            FROM intelligence
            WHERE timestamp >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY DATE_TRUNC('day', timestamp)
        )
        SELECT day, completed_count, with_relations_count, relation_item_count
        FROM day_bucket
        ORDER BY day ASC
    """)
    trend_rows = db.execute(trend_sql, {"days": safe_days}).all()
    trend = []
    for row in trend_rows:
        mapped = dict(row._mapping)
        day_completed = int(mapped.get("completed_count") or 0)
        day_with_rel = int(mapped.get("with_relations_count") or 0)
        day_rel_items = int(mapped.get("relation_item_count") or 0)
        trend.append({
            "day": mapped.get("day"),
            "completed_count": day_completed,
            "with_relations_count": day_with_rel,
            "relation_item_count": day_rel_items,
            "relation_coverage_pct": round((day_with_rel / day_completed) * 100, 2) if day_completed else 0.0,
            "avg_relations_per_event": round((day_rel_items / day_with_rel), 3) if day_with_rel else 0.0,
        })

    safe_baseline_days = max(3, min(120, int(baseline_days)))
    baseline_sql = text("""
        WITH current_window AS (
            SELECT
                COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_count,
                COUNT(*) FILTER (
                    WHERE status = 'COMPLETED'
                      AND relation_triples IS NOT NULL
                      AND jsonb_typeof(relation_triples) = 'array'
                      AND jsonb_array_length(relation_triples) > 0
                ) AS with_relations_count
            FROM intelligence
            WHERE timestamp >= NOW() - (:curr_days * INTERVAL '1 day')
        ),
        prev_window AS (
            SELECT
                COUNT(*) FILTER (WHERE status = 'COMPLETED') AS completed_count,
                COUNT(*) FILTER (
                    WHERE status = 'COMPLETED'
                      AND relation_triples IS NOT NULL
                      AND jsonb_typeof(relation_triples) = 'array'
                      AND jsonb_array_length(relation_triples) > 0
                ) AS with_relations_count
            FROM intelligence
            WHERE timestamp < NOW() - (:curr_days * INTERVAL '1 day')
              AND timestamp >= NOW() - ((:curr_days + :base_days) * INTERVAL '1 day')
        )
        SELECT
            current_window.completed_count AS current_completed_count,
            current_window.with_relations_count AS current_with_relations_count,
            prev_window.completed_count AS baseline_completed_count,
            prev_window.with_relations_count AS baseline_with_relations_count
        FROM current_window, prev_window
    """)
    baseline_row = db.execute(baseline_sql, {"curr_days": safe_days, "base_days": safe_baseline_days}).first()
    baseline_metrics = dict(baseline_row._mapping) if baseline_row else {}
    current_completed_count = int(baseline_metrics.get("current_completed_count") or 0)
    current_with_relations_count = int(baseline_metrics.get("current_with_relations_count") or 0)
    baseline_completed_count = int(baseline_metrics.get("baseline_completed_count") or 0)
    baseline_with_relations_count = int(baseline_metrics.get("baseline_with_relations_count") or 0)
    current_coverage = round((current_with_relations_count / current_completed_count) * 100, 2) if current_completed_count else 0.0
    baseline_coverage = round((baseline_with_relations_count / baseline_completed_count) * 100, 2) if baseline_completed_count else 0.0
    coverage_delta = round(current_coverage - baseline_coverage, 2)

    alerts = build_graph_quality_alerts(
        coverage_pct=coverage_pct,
        in_vocab_pct=in_vocab_pct,
        valid_direction_pct=valid_direction_pct,
        malformed_pct=malformed_pct,
        coverage_threshold=coverage_threshold,
        in_vocab_threshold=in_vocab_threshold,
        direction_threshold=direction_threshold,
        malformed_threshold=malformed_threshold,
    )

    return v1_prepare_json({
        "window_days": safe_days,
        "summary": {
            "completed_count": completed_count,
            "with_relations_count": with_relations_count,
            "relation_item_count": relation_item_count,
            "relation_coverage_pct": coverage_pct,
            "avg_relations_per_event": avg_relations_per_item,
        },
        "quality": {
            "total_relation_items": total_items,
            "malformed_items": malformed_items,
            "malformed_pct": malformed_pct,
            "valid_direction_pct": valid_direction_pct,
            "in_vocab_items": in_vocab_items,
            "in_vocab_pct": in_vocab_pct,
        },
        "alerts": alerts,
        "thresholds": {
            "coverage_threshold": coverage_threshold,
            "in_vocab_threshold": in_vocab_threshold,
            "direction_threshold": direction_threshold,
            "malformed_threshold": malformed_threshold,
        },
        "daily_report": {
            "days": safe_days,
            "trend": trend,
            "report_date": datetime.utcnow().date(),
        },
        "version_compare": {
            "current_days": safe_days,
            "baseline_days": safe_baseline_days,
            "coverage": {
                "current": current_coverage,
                "baseline": baseline_coverage,
                "delta": coverage_delta,
            },
        },
        "generated_at": datetime.utcnow(),
    })


@router.get("/sources/dashboard", response_model=Dict[str, Any])
async def get_web_sources_dashboard(
    days: int = 14,
    limit: int = 15,
    db: Session = Depends(get_session)
):
    """
    信源监控 Dashboard 数据：
    - 榜单：各信源命中率/样本数/最近活跃时间
    - 趋势：按天统计 top sources 命中率
    - 概览：总信源数/总样本数/总体命中率
    """
    safe_days = max(3, min(90, int(days)))
    safe_limit = max(5, min(50, int(limit)))

    leaderboard_sql = text("""
        SELECT
            source_name,
            COUNT(*) AS total_signals,
            SUM(CASE
                WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                ELSE 0
            END) AS hits,
            ROUND(
                (
                    SUM(CASE
                        WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                        WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                        ELSE 0
                    END)::numeric
                    / NULLIF(COUNT(*), 0)
                ) * 100, 2
            ) AS accuracy_pct,
            ROUND(
                (
                    (SUM(CASE
                        WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                        WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                        ELSE 0
                    END)::numeric + 1.9208)
                    / (COUNT(*) + 3.8416)
                    - 1.96 * SQRT(
                        (
                            SUM(CASE
                                WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                                WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                                ELSE 0
                            END)::numeric
                            * (COUNT(*) - SUM(CASE
                                WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                                WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                                ELSE 0
                            END)::numeric)
                            / NULLIF(COUNT(*), 0)
                            + 0.9604
                        )
                        / (COUNT(*) + 3.8416)
                    )
                ) * 100, 2
            ) AS accuracy_lower_bound,
            MAX(timestamp) AS last_seen
        FROM intelligence
        WHERE status = 'COMPLETED'
          AND source_name IS NOT NULL
          AND sentiment_score IS NOT NULL
          AND gold_price_snapshot IS NOT NULL
          AND price_1h IS NOT NULL
          AND ABS(sentiment_score) > 0.2
          AND timestamp >= NOW() - (:days * INTERVAL '1 day')
        GROUP BY source_name
        HAVING COUNT(*) >= 20
        ORDER BY accuracy_lower_bound DESC NULLS LAST, total_signals DESC
        LIMIT :limit
    """)
    leaderboard_rows = db.execute(leaderboard_sql, {"days": safe_days, "limit": safe_limit}).all()
    leaderboard = [dict(row._mapping) for row in leaderboard_rows]
    top_source_names = [row["source_name"] for row in leaderboard]

    trend = []
    if top_source_names:
        trend_sql = text("""
            SELECT
                DATE_TRUNC('day', timestamp) AS day,
                source_name,
                COUNT(*) AS total_signals,
                ROUND(
                    (
                        SUM(CASE
                            WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                            WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                            ELSE 0
                        END)::numeric
                        / NULLIF(COUNT(*), 0)
                    ) * 100, 2
                ) AS accuracy_pct
            FROM intelligence
            WHERE status = 'COMPLETED'
              AND source_name IS NOT NULL
              AND sentiment_score IS NOT NULL
              AND gold_price_snapshot IS NOT NULL
              AND price_1h IS NOT NULL
              AND ABS(sentiment_score) > 0.2
              AND timestamp >= NOW() - (:days * INTERVAL '1 day')
            GROUP BY DATE_TRUNC('day', timestamp), source_name
            ORDER BY day ASC, source_name ASC
        """)
        trend_rows = db.execute(trend_sql, {"days": safe_days}).all()
        top_name_set = set(top_source_names)
        trend = [dict(row._mapping) for row in trend_rows if row._mapping.get("source_name") in top_name_set]

    overview_sql = text("""
        WITH scored AS (
            SELECT
                source_name,
                CASE
                    WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                    WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                    ELSE 0
                END AS hit
            FROM intelligence
            WHERE status = 'COMPLETED'
              AND source_name IS NOT NULL
              AND sentiment_score IS NOT NULL
              AND gold_price_snapshot IS NOT NULL
              AND price_1h IS NOT NULL
              AND ABS(sentiment_score) > 0.2
              AND timestamp >= NOW() - (:days * INTERVAL '1 day')
        )
        SELECT
            COUNT(DISTINCT source_name) AS active_sources,
            COUNT(*) AS total_signals,
            ROUND(AVG(hit)::numeric * 100, 2) AS overall_accuracy_pct
        FROM scored
    """)
    overview_row = db.execute(overview_sql, {"days": safe_days}).first()
    overview = dict(overview_row._mapping) if overview_row else {
        "active_sources": 0, "total_signals": 0, "overall_accuracy_pct": None
    }

    return v1_prepare_json({
        "window_days": safe_days,
        "leaderboard": leaderboard,
        "trend": trend,
        "overview": overview,
        "generated_at": datetime.utcnow(),
    })

@router.get("/intelligence/{item_id}", response_model=Dict[str, Any])
async def get_web_intelligence_item(
    item_id: int,
    db: Session = Depends(get_session)
):
    """Fetch a single intelligence item with full JSONB content for Web."""
    statement = select(Intelligence).where(Intelligence.id == item_id)
    result = db.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return _with_confidence(result)


@router.get("/funds/search", response_model=Dict[str, Any])
async def search_web_funds(q: str = "", limit: int = 20):
    """Search for funds via Web BFF."""
    engine = FundEngine()
    results = engine.search_funds(q.strip(), limit)
    return v1_prepare_json({
        "results": results,
        "total": len(results),
        "query": q
    })

@router.get("/market", response_model=Dict[str, Any])
async def get_web_market_data(
    symbol: str = "GC=F", 
    range: str = "1d", 
    interval: str = "5m"
):
    """Fetch market data and indicators via Web BFF."""
    import akshare as ak
    from datetime import datetime
    from src.alphasignal.services.market_service import market_service
    
    try:
        # 1. Fetch Chart Data
        if symbol == "GC=F":
            df = ak.futures_global_hist_em(symbol="GC00Y")
        else:
            df = ak.stock_zh_a_hist(symbol=symbol.replace("sh", "").replace("sz", ""), period="daily", adjust="qfq")
            
        if df.empty:
            return {"symbol": symbol, "data": [], "indicators": None}
            
        quotes = []
        for _, row in df.tail(100).iterrows():
            date_str = str(row.get('日期') or row.get('date'))
            # Format for Plotly expected structure
            quotes.append({
                "date": date_str,
                "open": float(row.get('开盘') or 0),
                "high": float(row.get('最高') or 0),
                "low": float(row.get('最低') or 0),
                "close": float(row.get('收盘') or row.get('最新价') or 0),
                "volume": float(row.get('成交量') or row.get('总量') or 0)
            })
            
        # 2. Fetch Calculated Indicators (Parity, Spread)
        indicators = None
        if symbol == "GC=F":
            indicators = market_service.get_gold_indicators()
            
        return v1_prepare_json({
            "symbol": symbol, 
            "quotes": quotes,
            "indicators": indicators
        })
    except Exception:
        # Log full exception details server-side, but return a generic error to the client
        logging.exception("Error fetching market data for symbol %s", symbol)
        return {"error": "Failed to fetch market data. Please try again later."}

@router.get("/stats", response_model=Dict[str, Any])
async def get_web_backtest_stats(
    window: str = "1h",
    min_score: int = 8,
    sentiment: str = "bearish",
    db: Session = Depends(get_session)
):
    """
    V1 Full Production Port of server-side backtesting logic.
    Restores all analytical modules for the professional reporting dashboard.
    """
    try:
        # Determine columns based on window
        window_map = {"15m": "price_15m", "1h": "price_1h", "4h": "price_4h", "12h": "price_12h", "24h": "price_24h"}
        outcome_col = window_map.get(window, "price_1h")
        
        # Define keywords and win condition
        if sentiment == 'bearish':
            keywords = "鹰|利空|下跌|风险|Bearish|Hawkish|Risk|Negative|Pressure"
            win_condition = "exit < entry"
        else:
            keywords = "鸽|利多|上涨|积极|Bullish|Dovish|Positive|Safe-haven|Support"
            win_condition = "exit > entry"

        cluster_window = "30 minutes"
        
        # Prepare Common SQL Fragments
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
            SELECT *, 
                   gold_price_snapshot as entry, 
                   {outcome_col} as exit
            FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        )
        """

        # 1. Global Stats
        query_global = f"""
        {base_cte}
        SELECT COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins,
            AVG((exit - entry) / entry) * 100 as avg_change_pct,
            AVG(clustering_score) as avg_clustering, AVG(exhaustion_score) as avg_exhaustion,
            AVG(dxy_snapshot) as avg_dxy, AVG(us10y_snapshot) as avg_us10y, AVG(gvz_snapshot) as avg_gvz,
            COUNT(CASE WHEN {win_condition} AND clustering_score <= 3 AND exhaustion_score <= 5 THEN 1 END)::float / 
            NULLIF(COUNT(CASE WHEN clustering_score <= 3 AND exhaustion_score <= 5 THEN 1 END), 0) * 100 as adj_win_rate
        FROM deduplicated_events;
        """
        
        # 2. Session Stats
        query_session = f"""
        {base_cte}
        SELECT market_session, COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins,
            AVG((exit - entry) / entry) * 100 as avg_change_pct
        FROM deduplicated_events
        WHERE market_session IS NOT NULL
        GROUP BY market_session;
        """

        # 3. Correlation (DXY)
        query_correlation = f"""
        {base_cte},
        stats AS (SELECT AVG(dxy_snapshot) as mid FROM intelligence WHERE dxy_snapshot IS NOT NULL),
        qualified AS (SELECT entry, exit, dxy_snapshot FROM deduplicated_events, stats)
        SELECT CASE WHEN dxy_snapshot > (SELECT mid FROM stats) THEN 'DXY_STRONG' ELSE 'DXY_WEAK' END as env,
            COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM qualified GROUP BY env;
        """

        # 4. Positioning (COT)
        query_positioning = f"""
        {base_cte},
        qualified AS (
            SELECT i.entry, i.exit, i.timestamp,
                (SELECT percentile FROM market_indicators WHERE indicator_name = 'COT_GOLD_NET' AND timestamp <= i.timestamp ORDER BY timestamp DESC LIMIT 1) as cot_pct
            FROM deduplicated_events i
        )
        SELECT CASE WHEN cot_pct >= 85 THEN 'OVERCROWDED_LONG' WHEN cot_pct <= 15 THEN 'OVERCROWDED_SHORT' ELSE 'NEUTRAL_POSITION' END as env,
            COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM qualified WHERE cot_pct IS NOT NULL GROUP BY env;
        """

        # 5. Volatility (GVZ)
        query_volatility = f"""
        {base_cte}
        SELECT CASE WHEN gvz_snapshot > 25 THEN 'HIGH_VOL' ELSE 'LOW_VOL' END as env,
            COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM deduplicated_events WHERE gvz_snapshot IS NOT NULL GROUP BY env;
        """

        # 6. Distribution
        query_dist = f"""
        {base_cte},
        returns AS (SELECT ((CAST(exit AS FLOAT) - entry) / entry) * 100 as ret FROM deduplicated_events)
        SELECT floor(ret / 0.5) * 0.5 as bin, COUNT(*) as count FROM returns GROUP BY bin ORDER BY bin ASC;
        """

        # 7. Evidence List (Items)
        query_items = f"""
        {base_cte}
        SELECT id, summary as title, timestamp, urgency_score as score, entry, exit,
            CASE WHEN {win_condition} THEN true ELSE false END as is_win,
            ((CAST(exit AS FLOAT) - entry) / entry) * 100 as change_pct
        FROM deduplicated_events ORDER BY timestamp DESC LIMIT 50;
        """

        # Execute all queries
        params = {'keywords': keywords, 'min_score': min_score}
        
        res_global = db.execute(text(query_global), params).mappings().first()
        if not res_global or res_global['count'] == 0:
            return {"count": 0, "winRate": 0, "avgDrop": 0}
            
        res_sessions = db.execute(text(query_session), params).mappings().all()
        res_corr = db.execute(text(query_correlation), params).mappings().all()
        res_pos = db.execute(text(query_positioning), params).mappings().all()
        res_vol = db.execute(text(query_volatility), params).mappings().all()
        res_dist = db.execute(text(query_dist), params).mappings().all()
        res_items = db.execute(text(query_items), params).mappings().all()

        # Format Response
        session_stats = [{
            "session": s['market_session'], "count": s['count'],
            "winRate": (s['wins'] / s['count']) * 100 if s['count'] > 0 else 0,
            "avgDrop": -(s['avg_change_pct'] or 0)
        } for s in res_sessions]

        correlation_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_corr}
        positioning_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_pos}
        volatility_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_vol}

        return v1_prepare_json({
            "count": res_global['count'],
            "winRate": (res_global['wins'] / res_global['count']) * 100,
            "adjWinRate": res_global['adj_win_rate'] or 0,
            "avgDrop": -(res_global['avg_change_pct'] or 0),
            "hygiene": {
                "avgClustering": res_global['avg_clustering'] or 0,
                "avgExhaustion": res_global['avg_exhaustion'] or 0,
                "avgDxy": res_global['avg_dxy'] or 0,
                "avgUs10y": res_global['avg_us10y'] or 0,
                "avgGvz": res_global['avg_gvz'] or 0
            },
            "correlation": correlation_stats,
            "positioning": positioning_stats,
            "volatility": volatility_stats,
            "distribution": res_dist,
            "sessionStats": session_stats,
            "items": res_items
        })
        
    except Exception as e:
        import traceback
        print(f"[API] Stats error: {traceback.format_exc()}")
        return {"error": str(e)}

@router.get("/admin/monitor", response_model=Dict[str, Any])
async def get_web_monitor_stats(current_user: User = Depends(get_current_user)):
    """
    Admin stats for Web monitor page.
    """
    db_legacy = IntelligenceDB()
    stats = db_legacy.get_reconciliation_stats()
    stats['heatmap'] = db_legacy.get_heatmap_stats()
    return v1_prepare_json(stats)
