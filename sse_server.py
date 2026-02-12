"""
SSE (Server-Sent Events) endpoint for real-time intelligence updates.

This module provides a streaming endpoint that pushes new intelligence data
to connected clients as soon as it's written to the database.
"""

# ... imports remaining the same ...
import asyncio
import json
from typing import List, AsyncGenerator
from fastapi import FastAPI, Request, Depends
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware # Import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import asynccontextmanager
from src.alphasignal.config import settings
from src.alphasignal.auth.router import router as auth_router
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User

# --- Broadcast System ---

class ConnectionManager:
    """Manages active SSE connections and broadcasts messages"""
    def __init__(self):
        self.active_connections: List[asyncio.Queue] = []

    async def connect(self) -> asyncio.Queue:
        queue = asyncio.Queue()
        self.active_connections.append(queue)
        print(f"[SSE] Client connected. Active: {len(self.active_connections)}")
        return queue

    def disconnect(self, queue: asyncio.Queue):
        if queue in self.active_connections:
            self.active_connections.remove(queue)
            print(f"[SSE] Client disconnected. Active: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        """Push message to all active queues"""
        for queue in self.active_connections:
            await queue.put(message)

manager = ConnectionManager()
# Global tracker for the broadcasting thread
global_last_id = 0

async def database_poller():
    """
    Background task:
    Solely responsible for polling the DB and broadcasting updates.
    Runs once, regardless of client count.
    """
    global global_last_id
    
    # 1. Init: Find the current max ID to start polling from
    # We don't want to broadcast old history to everyone on startup
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(id), 0) FROM intelligence")
        global_last_id = cursor.fetchone()[0]
        conn.close()
        print(f"[Broadcaster] Started monitoring from ID: {global_last_id}")
    except Exception as e:
        print(f"[Broadcaster] Startup DB error: {e}")
        return

    # 2. Polling Loop
    while True:
        try:
            # Only poll if there are active clients (Optional optimization)
            # if not manager.active_connections:
            #     await asyncio.sleep(2)
            #     continue

            conn = psycopg2.connect(
                 host=settings.POSTGRES_HOST,
                 port=settings.POSTGRES_PORT,
                 user=settings.POSTGRES_USER,
                 password=settings.POSTGRES_PASSWORD,
                 dbname=settings.POSTGRES_DB
            )
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute(
                "SELECT * FROM intelligence WHERE id > %s ORDER BY id ASC LIMIT 50",
                (global_last_id,)
            )
            new_items = cursor.fetchall()
            conn.close()

            if new_items:
                items_data = [dict(row) for row in new_items]
                global_last_id = new_items[-1]['id']
                
                event_data = {
                    'type': 'intelligence_update',
                    'data': items_data,
                    'count': len(items_data),
                    'latest_id': global_last_id
                }
                msg = f"data: {json.dumps(event_data, default=str)}\n\n"
                
                await manager.broadcast(msg)
                print(f"[Broadcaster] Broadcasted {len(items_data)} new items")

        except Exception as e:
            print(f"[Broadcaster] Error: {e}")

        await asyncio.sleep(2)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    task = asyncio.create_task(database_poller())
    yield
    # Shutdown
    task.cancel()

from fastapi.staticfiles import StaticFiles
import os

app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure uploads directory exists
upload_dir = os.path.join(settings.BASE_DIR, "uploads")
os.makedirs(upload_dir, exist_ok=True)

# Mount static files for avatars/etc.
app.mount("/static", StaticFiles(directory=upload_dir), name="static")

# Register Routers
app.include_router(auth_router)

# --- Endpoints ---


@app.get("/api/funds/{code}/valuation")
async def get_fund_valuation(code: str):
    """Get real-time estimated valuation for a fund."""
    from src.alphasignal.core.fund_engine import FundEngine
    
    engine = FundEngine()
    # Use efficient batch method even for single fund
    try:
        results = engine.calculate_batch_valuation([code])
        if results:
            # Enrich with stats
            from src.alphasignal.core.database import IntelligenceDB
            db = IntelligenceDB()
            stats_map = db.get_fund_stats([code])
            if code in stats_map:
                results[0]['stats'] = stats_map[code]
            return results[0]
        return {"error": "Valuation failed"}
    except AttributeError:
        # Fallback
        return engine.calculate_realtime_valuation(code)

@app.post("/api/funds/{code}/refresh")
async def refresh_fund_holdings(code: str):
    """Force refresh of fund holdings (e.g. new quarter released)."""
    from src.alphasignal.core.fund_engine import FundEngine
    engine = FundEngine()
    holdings = engine.update_fund_holdings(code)
    return {"status": "ok", "holdings_count": len(holdings)}

@app.get("/api/funds/batch-valuation")
async def get_batch_valuations(codes: str, mode: str = "full"):
    """
    Get real-time valuations for multiple funds.
    codes: Comma-separated list of fund codes.
    mode: 'full' (all data) or 'summary' (only growth)
    """
    import time
    if not codes:
        return {"data": []}
    
    code_list = [c.strip() for c in codes.split(',') if c.strip()]
    if not code_list:
        return {"data": []}

    from src.alphasignal.core.fund_engine import FundEngine
    engine = FundEngine()
    
    # Use optimized batch valuation
    try:
        results = engine.calculate_batch_valuation(code_list, summary=(mode == "summary"))
        
        # Enrich with stats
        from src.alphasignal.core.database import IntelligenceDB
        db = IntelligenceDB()
        stats_map = db.get_fund_stats(code_list)
        
        for res in results:
            f_code = res.get('fund_code')
            if f_code in stats_map:
                res['stats'] = stats_map[f_code]
                
        return {"data": results}
    except AttributeError:
        # Fallback if method missing (during partial reload)
        results = []
        for code in code_list[:20]:
            try:
                val = engine.calculate_realtime_valuation(code)
                results.append(val)
            except Exception as e:
                results.append({"fund_code": code, "error": str(e)})
        return {"data": results}
    except Exception as e:
        return {"data": [], "error": str(e)}

@app.get("/api/funds/{code}/history")
async def get_fund_history(code: str, limit: int = 30):
    """Get historical valuation vs official performance for a fund."""
    from src.alphasignal.core.database import IntelligenceDB
    db = IntelligenceDB()
    history = db.get_valuation_history(code, limit)
    # Ensure date objects are serializable
    formatted_history = []
    for h in history:
        item = dict(h)
        if 'trade_date' in item and hasattr(item['trade_date'], 'isoformat'):
            item['trade_date'] = item['trade_date'].isoformat()
        formatted_history.append(item)
    return {"data": formatted_history}

@app.post("/api/admin/funds/snapshot")
async def trigger_snapshot():
    """Admin: Manually trigger 15:00 valuation snapshot."""
    from src.alphasignal.core.fund_engine import FundEngine
    engine = FundEngine()
    engine.take_all_funds_snapshot()
    return {"status": "snapshot_triggered"}

@app.post("/api/admin/funds/reconcile")
async def trigger_reconcile(date: str = None):
    """Admin: Manually trigger official NAV reconciliation."""
    from src.alphasignal.core.fund_engine import FundEngine
    engine = FundEngine()
    target_date = None
    if date:
        from datetime import datetime
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD"}
    engine.reconcile_official_valuations(target_date)
    return {"status": "reconciliation_triggered", "date": str(target_date)}

# --- Watchlist APIs ---
from pydantic import BaseModel

class WatchlistItem(BaseModel):
    code: str
    name: str

@app.get("/api/admin/funds/monitor")
async def get_fund_monitor_stats(current_user: User = Depends(get_current_user)):
    """Admin: Get reconciliation performance and system health stats."""
    from src.alphasignal.core.database import IntelligenceDB
    db = IntelligenceDB()
    stats = db.get_reconciliation_stats()
    return stats

@app.get("/api/watchlist")
async def get_watchlist(current_user: User = Depends(get_current_user)):
    from src.alphasignal.core.database import IntelligenceDB
    db = IntelligenceDB()
    rows = db.get_watchlist(str(current_user.id))
    # Simplify response
    return {"data": [{"code": r['fund_code'], "name": r['fund_name']} for r in rows]}

@app.post("/api/watchlist")
async def add_to_watchlist(item: WatchlistItem, current_user: User = Depends(get_current_user)):
    from src.alphasignal.core.database import IntelligenceDB
    db = IntelligenceDB()
    success = db.add_to_watchlist(item.code, item.name, str(current_user.id))
    return {"success": success}

@app.delete("/api/watchlist/{code}")
async def remove_from_watchlist(code: str, current_user: User = Depends(get_current_user)):
    from src.alphasignal.core.database import IntelligenceDB
    db = IntelligenceDB()
    success = db.remove_from_watchlist(code, str(current_user.id))
    return {"success": success}

@app.get("/api/funds/search")
async def search_funds(q: str = "", limit: int = 20):
    """
    Search for funds by code or name.
    
    Args:
        q: Search query (fund code or name)
        limit: Maximum number of results (default 20, max 50)
    
    Returns:
        List of matching funds with code, name, type, and company
    """
    from src.alphasignal.core.fund_engine import FundEngine
    
    if not q or len(q.strip()) == 0:
        return {"results": [], "total": 0}
    
    # Limit max results to 50
    limit = min(limit, 50)
    
    engine = FundEngine()
    results = engine.search_funds(q.strip(), limit)
    
    return {
        "results": results,
        "total": len(results),
        "query": q
    }

@app.get("/api/stats")
async def get_backtest_stats(request: Request):
    """
    Calculate backtest statistics on the SERVER side using the full database history.
    Supports window, min_score, and sentiment_type parameters.
    """
    window = request.query_params.get('window', '1h')
    min_score = int(request.query_params.get('min_score', 8))
    sentiment_type = request.query_params.get('sentiment', 'bearish') # 'bearish' or 'bullish'
    
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Determine columns based on window
        window_map = {
            "15m": "price_15m",
            "1h": "price_1h",
            "4h": "price_4h",
            "12h": "price_12h",
            "24h": "price_24h"
        }
        outcome_col = window_map.get(window, "price_1h")
        
        # Define keywords based on sentiment type
        if sentiment_type == 'bearish':
            keywords = "鹰|利空|下跌|风险|Bearish|Hawkish|Risk|Negative|Pressure"
            win_condition = "exit < entry" # Profit from price drop
        else:
            keywords = "鸽|利多|上涨|积极|Bullish|Dovish|Positive|Safe-haven|Support"
            win_condition = "exit > entry" # Profit from price rise

        # Clustering Logic: Group signals within 30 minutes and pick the first one
        cluster_window = "30 minutes"
        
        # 1. Global Stats (Raw)
        query_global = f"""
        WITH filtered_intelligence AS (
            -- This CTE removes clustered signals: only the first signal in a 30min window is kept
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified_events AS (
            SELECT 
                gold_price_snapshot as entry,
                {outcome_col} as exit,
                clustering_score,
                exhaustion_score,
                dxy_snapshot,
                us10y_snapshot,
                gvz_snapshot
            FROM deduplicated_events
        )
        SELECT 
            COUNT(*) as count,
            COUNT(CASE WHEN {win_condition} THEN 1 END) as wins,
            AVG((exit - entry) / entry) * 100 as avg_change_pct,
            AVG(clustering_score) as avg_clustering,
            AVG(exhaustion_score) as avg_exhaustion,
            
            -- Correlation Stats
            AVG(dxy_snapshot) as avg_dxy,
            AVG(us10y_snapshot) as avg_us10y,
            AVG(gvz_snapshot) as avg_gvz,
            
            -- Adjusted Win Rate: Exclude noise
            COUNT(CASE WHEN {win_condition} AND clustering_score <= 3 AND exhaustion_score <= 5 THEN 1 END)::float / 
            NULLIF(COUNT(CASE WHEN clustering_score <= 3 AND exhaustion_score <= 5 THEN 1 END), 0) * 100 as adj_win_rate
        FROM qualified_events;
        """
        
        # 1.5 Distribution Stats
        query_dist = f"""
        WITH filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        returns AS (
            SELECT ((CAST({outcome_col} AS FLOAT) - gold_price_snapshot) / gold_price_snapshot) * 100 as ret
            FROM deduplicated_events
        )
        SELECT 
            floor(ret / 0.5) * 0.5 as bin,
            COUNT(*) as count
        FROM returns
        GROUP BY bin
        ORDER BY bin ASC;
        """
        
        # 2. Session Stats
        query_session = f"""
        WITH filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
              AND market_session IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified_events AS (
            SELECT 
                market_session,
                gold_price_snapshot as entry,
                {outcome_col} as exit
            FROM deduplicated_events
        )
        SELECT 
            market_session,
            COUNT(*) as count,
            COUNT(CASE WHEN {win_condition} THEN 1 END) as wins,
            AVG((exit - entry) / entry) * 100 as avg_change_pct
        FROM qualified_events
        GROUP BY market_session;
        """

        # 3. Correlation Breakdown (DXY sensitivity)
        query_correlation = f"""
        WITH stats AS (SELECT AVG(dxy_snapshot) as mid FROM intelligence WHERE dxy_snapshot IS NOT NULL),
        filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
              AND dxy_snapshot IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified AS (
            SELECT 
                gold_price_snapshot as entry,
                {outcome_col} as exit,
                dxy_snapshot
            FROM deduplicated_events, stats
        )
        SELECT 
            CASE WHEN dxy_snapshot > (SELECT mid FROM stats) THEN 'DXY_STRONG' ELSE 'DXY_WEAK' END as env,
            COUNT(*) as count,
            COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM qualified
        GROUP BY env;
        """

        # 4. Positioning Overhang (COT)
        query_positioning = f"""
        WITH filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified AS (
            SELECT 
                i.gold_price_snapshot as entry,
                i.{outcome_col} as exit,
                (SELECT percentile FROM market_indicators 
                 WHERE indicator_name = 'COT_GOLD_NET' AND timestamp <= i.timestamp 
                 ORDER BY timestamp DESC LIMIT 1) as cot_pct
            FROM deduplicated_events i
        )
        SELECT 
            CASE 
                WHEN cot_pct >= 85 THEN 'OVERCROWDED_LONG'
                WHEN cot_pct <= 15 THEN 'OVERCROWDED_SHORT'
                else 'NEUTRAL_POSITION'
            END as env,
            COUNT(*) as count,
            COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM qualified
        WHERE cot_pct IS NOT NULL
        GROUP BY env;
        """

        # 5. Volatility Regime (GVZ)
        query_volatility = f"""
        WITH filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
              AND gvz_snapshot IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified AS (
            SELECT 
                gold_price_snapshot as entry,
                {outcome_col} as exit,
                gvz_snapshot
            FROM deduplicated_events
        )
        SELECT 
            CASE WHEN gvz_snapshot > 25 THEN 'HIGH_VOL' ELSE 'LOW_VOL' END as env,
            COUNT(*) as count,
            COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM qualified
        GROUP BY env;
        """
        
        # 6. Macro Regime (Fed Basis)
        query_macro = f"""
        WITH filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        qualified AS (
            SELECT 
                i.gold_price_snapshot as entry,
                i.{outcome_col} as exit,
                (SELECT value FROM market_indicators 
                 WHERE indicator_name = 'FED_REGIME' AND timestamp <= i.timestamp 
                 ORDER BY timestamp DESC LIMIT 1) as fed_val
            FROM deduplicated_events i
        )
        SELECT 
            CASE 
                WHEN fed_val > 0 THEN 'DOVISH_REGIME'
                WHEN fed_val < 0 THEN 'HAWKISH_REGIME'
                ELSE 'NEUTRAL_REGIME'
            END as env,
            COUNT(*) as count,
            COUNT(CASE WHEN {win_condition} THEN 1 END) as wins
        FROM qualified
        GROUP BY env;
        """
        
        # 7. Detailed Items
        query_items = f"""
        WITH filtered_intelligence AS (
            SELECT *,
                   LAG(timestamp) OVER (ORDER BY timestamp ASC) as prev_timestamp
            FROM intelligence
            WHERE urgency_score >= %(min_score)s
              AND (sentiment::text ~* %(keywords)s)
              AND gold_price_snapshot IS NOT NULL 
              AND {outcome_col} IS NOT NULL
        ),
        deduplicated_events AS (
            SELECT * FROM filtered_intelligence
            WHERE prev_timestamp IS NULL 
               OR timestamp > prev_timestamp + INTERVAL '{cluster_window}'
        ),
        raw_items AS (
            SELECT 
                id,
                summary as title,
                timestamp,
                urgency_score as score,
                gold_price_snapshot as entry,
                {outcome_col} as exit
            FROM deduplicated_events
        )
        SELECT 
            *,
            CASE WHEN {win_condition} THEN true ELSE false END as is_win,
            ((CAST(exit AS FLOAT) - entry) / entry) * 100 as change_pct
        FROM raw_items
        ORDER BY timestamp DESC
        LIMIT 50;
        """
        
        cursor.execute(query_global, {'keywords': keywords, 'min_score': min_score})
        res_global = cursor.fetchone()
        
        cursor.execute(query_session, {'keywords': keywords, 'min_score': min_score})
        res_sessions = cursor.fetchall()

        cursor.execute(query_correlation, {'keywords': keywords, 'min_score': min_score})
        res_corr = cursor.fetchall()

        cursor.execute(query_positioning, {'keywords': keywords, 'min_score': min_score})
        res_pos = cursor.fetchall()

        cursor.execute(query_volatility, {'keywords': keywords, 'min_score': min_score})
        res_vol = cursor.fetchall()

        cursor.execute(query_macro, {'keywords': keywords, 'min_score': min_score})
        res_macro = cursor.fetchall()

        cursor.execute(query_dist, {'keywords': keywords, 'min_score': min_score})
        res_dist = cursor.fetchall()

        cursor.execute(query_items, {'keywords': keywords, 'min_score': min_score})
        res_items = cursor.fetchall()
        
        if not res_global or res_global['count'] == 0:
            return {"count": 0, "winRate": 0, "avgDrop": 0, "window": window, "sessionStats": [], "items": [], "distribution": []}
            
        session_stats = []
        for s in res_sessions:
            session_stats.append({
                "session": s['market_session'],
                "count": s['count'],
                "winRate": (s['wins'] / s['count']) * 100 if s['count'] > 0 else 0,
                "avgDrop": -(s['avg_change_pct'] or 0)
            })

        correlation_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_corr}
        positioning_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_pos}
        volatility_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_vol}
        macro_stats = {row['env']: {"count": row['count'], "winRate": (row['wins']/row['count'])*100} for row in res_macro}

        return {
            "count": res_global['count'],
            "winRate": (res_global['wins'] / res_global['count']) * 100,
            "adjWinRate": res_global['adj_win_rate'] or 0,
            "avgDrop": -(res_global['avg_change_pct'] or 0),
            "hygiene": {
                "avgClustering": res_global['avg_clustering'] or 0,
                "avgExhaustion": res_global['avg_exhaustion'] or 0,
                "avgDxy": res_global['avg_dxy'] or 0,
                "avgUs10y": res_global['avg_us10y'] or 0,
                "avgGvz": res_global['avg_gvz'] or 0 if 'avg_gvz' in res_global else 0
            },
            "correlation": correlation_stats,
            "positioning": positioning_stats,
            "volatility": volatility_stats,
            "macro": macro_stats,
            "distribution": res_dist,
            "window": window,
            "sessionStats": session_stats,
            "items": res_items
        }
        
    except Exception as e:
        print(f"[API] Stats error: {e}")
        return {"error": str(e)}

@app.get("/api/alerts/24h")
async def get_24h_alerts_count():
    """
    Get the count of high-urgency (score 8+) alerts in the last 24 hours.
    """
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        cursor = conn.cursor()
        
        query = """
        SELECT COUNT(*) 
        FROM intelligence 
        WHERE urgency_score >= 8 
        AND timestamp > NOW() - INTERVAL '24 hours'
        """
        
        cursor.execute(query)
        result = cursor.fetchone()
        conn.close()
        
        return {"count": result[0] if result else 0}
        
    except Exception as e:
        print(f"[API] 24h Alerts error: {e}")
        return {"error": str(e)}

@app.get("/api/intelligence/stream")
async def intelligence_stream(request: Request):
    """
    SSE Endpoint.
    1. Fetches initial history (context) for this specific client.
    2. Subscribes client to global broadcast for future updates.
    """
    async def event_generator():
        # A. Send Connection Ack
        yield f"data: {json.dumps({'type': 'connected', 'message': 'SSE stream established'})}\n\n"
        
        # B. Send Initial Context (History)
        # This is the ONLY time this client queries the DB directly
        since_id_param = request.query_params.get('since_id')
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                dbname=settings.POSTGRES_DB
            )
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if since_id_param:
                # Resume: fetch everything since provided ID
                try:
                    target_id = int(since_id_param)
                    cursor.execute("SELECT * FROM intelligence WHERE id > %s ORDER BY id ASC LIMIT 50", (target_id,))
                except ValueError:
                    cursor.execute("SELECT * FROM intelligence ORDER BY id DESC LIMIT 50")
            else:
                # Default: fetch last 50
                cursor.execute("SELECT * FROM intelligence ORDER BY id DESC LIMIT 50")

            initial_items = cursor.fetchall()
            conn.close()

            if initial_items:
                # If we fetched via DESC, reverse to make it ASC
                if not since_id_param or (since_id_param and 'DESC' in cursor.query.decode()):
                     # Note: logic above uses ASC for resume, DESC for default.
                     # Simplified: If fetched by DESC, reverse it.
                     if not since_id_param:
                         initial_items.reverse()

                items_data = [dict(row) for row in initial_items]
                if items_data:
                    last_id = items_data[-1]['id']
                    
                    event_payload = {
                        'type': 'intelligence_update', 
                        'data': items_data, 
                        'count': len(items_data),
                        'latest_id': last_id
                    }
                    yield f"data: {json.dumps(event_payload, default=str)}\n\n"
        except Exception as e:
            print(f"[SSE] Initial fetch error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'Initial fetch failed'})}\n\n"

        # C. Switch to Broadcast Mode
        queue = await manager.connect()
        try:
            while True:
                if await request.is_disconnected():
                    break
                # Wait for new data from global broadcaster
                data = await queue.get()
                yield data
        finally:
            manager.disconnect(queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.get("/api/intelligence/{item_id}")
async def get_intelligence_item(item_id: int):
    """Fetch a single intelligence item by ID."""
    try:
        conn = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB
        )
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT * FROM intelligence WHERE id = %s", (item_id,))
        item = cursor.fetchone()
        conn.close()
        
        if not item:
            return {"error": "Item not found"}, 404
            
        return item
    except Exception as e:
        print(f"[API] Fetch intelligence error: {e}")
        return {"error": str(e)}, 500

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "AlphaSignal SSE (Broadcast Mode)"}

if __name__ == "__main__":
    import uvicorn
    # In raw python execution, lifespan works automatically with uvicorn.run(app)
    uvicorn.run(app, host="0.0.0.0", port=8001)
