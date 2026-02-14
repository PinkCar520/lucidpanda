from fastapi import APIRouter, Depends, Query, Request
from sqlmodel import Session, select
from typing import List, Dict, Any, Optional
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.fund import FundMetadata, FundValuationArchive
from src.alphasignal.models.intelligence import Intelligence
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.core.fund_engine import FundEngine
from src.alphasignal.core.database import IntelligenceDB

router = APIRouter()

@router.get("/watchlist", response_model=Dict[str, Any])
async def get_web_watchlist(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get user's watchlist for Web.
    Maintains the {"data": [...]} wrapper for TanStack Query compatibility.
    """
    # Reusing the existing IntelligenceDB logic for now to ensure consistency
    # In a later phase, we can refactor this to pure SQLModel
    db_legacy = IntelligenceDB()
    rows = db_legacy.get_watchlist(str(current_user.id))
    return {"data": [{"code": r['fund_code'], "name": r['fund_name']} for r in rows]}

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
            
    return decimal_to_float({"data": results})

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
        return decimal_to_float(results[0])
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
    return decimal_to_float({"data": formatted_history})

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
    return {"data": results}

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

@router.get("/intelligence/{item_id}", response_model=Intelligence)
async def get_web_intelligence_item(
    item_id: int,
    db: Session = Depends(get_session)
):
    """Fetch a single intelligence item with full JSONB content for Web."""
    statement = select(Intelligence).where(Intelligence.id == item_id)
    result = db.exec(statement).first()
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Item not found")
    return result

@router.get("/funds/search", response_model=Dict[str, Any])
async def search_web_funds(q: str = "", limit: int = 20):
    """Search for funds via Web BFF."""
    engine = FundEngine()
    results = engine.search_funds(q.strip(), limit)
    return {
        "results": results,
        "total": len(results),
        "query": q
    }

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
            df = ak.futures_foreign_hist_em(symbol="GC")
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
                "close": float(row.get('收盘') or 0),
                "volume": float(row.get('成交量') or 0)
            })
            
        # 2. Fetch Calculated Indicators (Parity, Spread)
        indicators = None
        if symbol == "GC=F":
            indicators = market_service.get_gold_indicators()
            
        return {
            "symbol": symbol, 
            "quotes": quotes, # Web Chart.tsx expects "quotes"
            "indicators": indicators
        }
    except Exception as e:
        return {"error": str(e)}

@router.get("/stats", response_model=Dict[str, Any])
async def get_web_backtest_stats(
    window: str = "1h",
    min_score: int = 8,
    sentiment: str = "bearish"
):
    """
    V1 Port of the complex server-side backtesting logic.
    """
    import psycopg2
    from psycopg2.extras import RealDictCursor
    from src.alphasignal.config import settings
    
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        window_map = {"15m": "price_15m", "1h": "price_1h", "4h": "price_4h", "12h": "price_12h", "24h": "price_24h"}
        outcome_col = window_map.get(window, "price_1h")
        
        if sentiment == 'bearish':
            keywords = "鹰|利空|下跌|风险|Bearish|Hawkish|Risk|Negative|Pressure"
            win_condition = "exit < entry"
        else:
            keywords = "鸽|利多|上涨|积极|Bullish|Dovish|Positive|Safe-haven|Support"
            win_condition = "exit > entry"

        cluster_window = "30 minutes"
        
        # 1. Global Stats
        query_global = f"""
        WITH filtered_intelligence AS (
            SELECT *, LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified_events AS (
            SELECT gold_price_snapshot as entry, {outcome_col} as exit, clustering_score, exhaustion_score, dxy_snapshot, us10y_snapshot, gvz_snapshot
            FROM deduplicated_events
        )
        SELECT COUNT(*) as count, COUNT(CASE WHEN {win_condition} THEN 1 END) as wins,
            AVG((exit - entry) / entry) * 100 as avg_change_pct,
            AVG(clustering_score) as avg_clustering, AVG(exhaustion_score) as avg_exhaustion,
            AVG(dxy_snapshot) as avg_dxy, AVG(us10y_snapshot) as avg_us10y,
            COUNT(CASE WHEN {win_condition} AND clustering_score <= 3 AND exhaustion_score <= 5 THEN 1 END)::float / 
            NULLIF(COUNT(CASE WHEN clustering_score <= 3 AND exhaustion_score <= 5 THEN 1 END), 0) * 100 as adj_win_rate
        FROM qualified_events;
        """
        
        cursor.execute(query_global, {'keywords': keywords, 'min_score': min_score})
        res_global = cursor.fetchone()
        conn.close()
        
        if not res_global or res_global['count'] == 0:
            return {"count": 0, "winRate": 0, "avgDrop": 0}

        return {
            "count": res_global['count'],
            "winRate": (res_global['wins'] / res_global['count']) * 100,
            "adjWinRate": res_global['adj_win_rate'] or 0,
            "avgDrop": -(res_global['avg_change_pct'] or 0),
            "hygiene": {
                "avgClustering": res_global['avg_clustering'] or 0,
                "avgExhaustion": res_global['avg_exhaustion'] or 0
            }
        }
    except Exception as e:
        return {"error": str(e)}

from decimal import Decimal

def decimal_to_float(obj):
    """Recursively convert Decimal objects to float."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj

@router.get("/admin/monitor", response_model=Dict[str, Any])
async def get_web_monitor_stats(current_user: User = Depends(get_current_user)):
    """
    Admin stats for Web monitor page.
    """
    db_legacy = IntelligenceDB()
    stats = db_legacy.get_reconciliation_stats()
    stats['heatmap'] = db_legacy.get_heatmap_stats()
    return decimal_to_float(stats)
