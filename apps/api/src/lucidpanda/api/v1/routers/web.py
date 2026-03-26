from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from src.lucidpanda.auth.dependencies import get_current_user
from src.lucidpanda.auth.models import User
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.fund_engine import FundEngine
from src.lucidpanda.core.logger import logger
from src.lucidpanda.infra.database.connection import get_session
from src.lucidpanda.services.fund_service import FundService
from src.lucidpanda.services.intelligence_service import IntelligenceService
from src.lucidpanda.services.market_service import MarketService, market_service
from src.lucidpanda.services.watchlist_service import WatchlistService
from src.lucidpanda.utils import v1_prepare_json

router = APIRouter()
def get_intelligence_service(db: Session = Depends(get_session)) -> IntelligenceService:
    return IntelligenceService(db)

def get_watchlist_service(db: Session = Depends(get_session)) -> WatchlistService:
    return WatchlistService(db)

def get_fund_service(db: Session = Depends(get_session)) -> FundService:
    return FundService(db)

@router.get("/watchlist", response_model=dict[str, Any])
async def get_web_watchlist(
    current_user: User = Depends(get_current_user),
    service: WatchlistService = Depends(get_watchlist_service)
):
    """
    Get user's watchlist for Web.
    Maintains the {"data": [...]} wrapper for TanStack Query compatibility.
    """
    try:
        items = service.get_watchlist(str(current_user.id))
        return v1_prepare_json({"data": items})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

@router.get("/funds/batch-valuation", response_model=dict[str, Any])
async def get_web_batch_valuations(
    codes: str,
    mode: str = "full",
    current_user: User = Depends(get_current_user),
    service: FundService = Depends(get_fund_service)
):
    """
    Batch valuation for Web with full data density.
    """
    if not codes:
        return {"data": []}

    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    results = service.get_batch_valuation(code_list, summary=(mode == "summary"))
    return v1_prepare_json({"data": results})

@router.get("/funds/{code}/valuation", response_model=dict[str, Any])
async def get_web_fund_valuation(
    code: str,
    current_user: User = Depends(get_current_user),
    service: FundService = Depends(get_fund_service)
):
    """
    Detailed single fund valuation for Web.
    """
    result = service.get_fund_valuation(code)
    if result:
        return v1_prepare_json(result)
    return {"error": "Valuation failed"}

@router.get("/funds/{code}/history", response_model=dict[str, Any])
async def get_web_fund_history(
    code: str,
    limit: int = 30,
    current_user: User = Depends(get_current_user),
    service: FundService = Depends(get_fund_service)
):
    """
    Historical performance for Web.
    """
    history = service.get_valuation_history(code, limit)
    return v1_prepare_json({"data": history})

@router.get("/intelligence/full", response_model=dict[str, Any])
async def get_web_intelligence_full(
    limit: int = 50,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """
    Returns full rich JSONB objects for Web localized rendering.
    """
    return {"data": service.get_intelligence_full(limit)}

from pydantic import BaseModel  # noqa: E402


class WatchlistItemDTO(BaseModel):
    code: str
    name: str

@router.post("/watchlist", response_model=dict[str, Any])
async def add_web_watchlist(
    item: WatchlistItemDTO,
    current_user: User = Depends(get_current_user)
):
    """Add a fund to watchlist via Web BFF."""
    db_legacy = IntelligenceDB()
    success = db_legacy.add_to_watchlist(item.code, item.name, str(current_user.id))
    return {"success": success}

@router.delete("/watchlist/{code}", response_model=dict[str, Any])
async def remove_web_watchlist(
    code: str,
    current_user: User = Depends(get_current_user)
):
    """Remove a fund from watchlist via Web BFF."""
    db_legacy = IntelligenceDB()
    success = db_legacy.remove_from_watchlist(code, str(current_user.id))
    return {"success": success}

@router.get("/intelligence/fused", response_model=dict[str, Any])
async def get_web_fused_intelligence(
    limit: int = 30,
    before_timestamp: str | None = None,
    force_refresh: bool = False,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """
    Fused intelligence view（NIE-like）
    """
    return service.get_fused_intelligence(limit, before_timestamp, force_refresh)


@router.post("/intelligence/fused/cache/invalidate", response_model=dict[str, Any])
async def invalidate_web_fused_cache(service: IntelligenceService = Depends(get_intelligence_service)):
    removed = service.invalidate_fused_cache()
    return v1_prepare_json({
        "success": True,
        "removed": removed,
        "invalidated_at": datetime.utcnow(),
    })


@router.get("/graph/event/{cluster_id}", response_model=dict[str, Any])
async def get_web_event_graph(
    cluster_id: str,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """按事件 cluster 返回知识图谱。"""
    return v1_prepare_json(service.get_event_graph(cluster_id))


@router.get("/graph/entity/{entity_name}", response_model=dict[str, Any])
async def get_web_entity_graph(
    entity_name: str,
    limit: int = 100,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """按实体返回邻接子图。"""
    return v1_prepare_json(service.get_entity_graph(entity_name, limit))


@router.get("/graph/path", response_model=dict[str, Any])
async def get_web_graph_path(
    from_entity: str,
    to_entity: str,
    max_hops: int = 2,
    min_confidence: float = 0.0,
    relation: str | None = None,
    event_cluster_id: str | None = None,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """查找两个实体之间的1~2跳路径。"""
    return v1_prepare_json(service.find_graph_path(
        from_entity, to_entity, max_hops, min_confidence, relation, event_cluster_id
    ))


@router.get("/graph/quality", response_model=dict[str, Any])
async def get_web_graph_quality(
    days: int = 14,
    baseline_days: int = 14,
    coverage_threshold: float = 60.0,
    in_vocab_threshold: float = 70.0,
    direction_threshold: float = 90.0,
    malformed_threshold: float = 20.0,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """图谱抽取质量快照。"""
    return v1_prepare_json(service.get_graph_quality(
        days, baseline_days, coverage_threshold, in_vocab_threshold, direction_threshold, malformed_threshold
    ))


@router.get("/sources/dashboard", response_model=dict[str, Any])
async def get_web_sources_dashboard(
    days: int = 14,
    limit: int = 15,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """信源监控 Dashboard 数据。"""
    return v1_prepare_json(service.get_sources_dashboard(days, limit))

@router.get("/intelligence/{item_id}", response_model=dict[str, Any])
async def get_web_intelligence_item(
    item_id: int,
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """Fetch a single intelligence item with full JSONB content for Web."""
    result = service.get_intelligence_item(item_id)
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")
    return result


@router.get("/funds/search", response_model=dict[str, Any])
async def search_web_funds(q: str = "", limit: int = 20):
    """Search for funds via Web BFF."""
    engine = FundEngine()
    results = engine.search_funds(q.strip(), limit)
    return v1_prepare_json({
        "results": results,
        "total": len(results),
        "query": q
    })

@router.get("/market", response_model=dict[str, Any])
async def get_web_market_data(
    symbol: str = "GC=F",
    range: str = "1d",
    interval: str = "5m",
    service: MarketService = Depends(lambda: market_service)
):
    """Fetch market data and indicators via Web BFF."""
    try:
        # 1. Fetch Chart Data
        quotes = service.get_market_quotes(symbol)

        # 2. Fetch Calculated Indicators (Parity, Spread)
        indicators = None
        if symbol == "GC=F":
            indicators = service.get_gold_indicators()

        return v1_prepare_json({
            "symbol": symbol,
            "quotes": quotes,
            "indicators": indicators
        })
    except Exception as e:
        logger.error(f"Error fetching market data for symbol {symbol}: {e}")
        return {"error": "Failed to fetch market data. Please try again later."}

@router.get("/stats", response_model=dict[str, Any])
async def get_web_backtest_stats(
    window: str = "1h",
    min_score: int = 8,
    sentiment: str = "bearish",
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """
    V1 Full Production Port of server-side backtesting logic.
    """
    try:
        return service.get_backtest_stats(window, min_score, sentiment)
    except Exception as e:
        logger.error(f"[API] Stats error: {e}")
        return {"error": str(e)}

@router.get("/admin/monitor", response_model=dict[str, Any])
async def get_web_monitor_stats(
    service: IntelligenceService = Depends(get_intelligence_service)
):
    """
    Admin stats for Web monitor page.
    """
    return v1_prepare_json(service.get_monitor_stats())

class ReconcileTriggerDTO(BaseModel):
    trade_date: str
    fund_code: str | None = None

@router.post("/admin/reconcile/trigger", response_model=dict[str, Any])
async def trigger_reconciliation(
    payload: ReconcileTriggerDTO,
    current_user: User = Depends(get_current_user),
    service: FundService = Depends(get_fund_service)
):
    """
    Trigger manual reconciliation for a specific date or fund.
    Allows administrators to fix data quality issues in real-time.
    """
    logger.info(f"🚀 Manual reconciliation triggered by user {current_user.id} for {payload.trade_date} (Code: {payload.fund_code or 'ALL'})")
    try:
        # Note: I should move the date parsing to service if needed, but keeping it here for now
        result = service.trigger_reconciliation(payload.fund_code)
        return v1_prepare_json(result)
    except Exception as e:
        logger.error(f"Manual reconciliation trigger failed: {e}")
        return {"success": False, "error": str(e)}
