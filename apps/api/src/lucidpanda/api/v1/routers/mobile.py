import json
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlmodel import Session, col, select, text

from src.lucidpanda.auth.dependencies import get_current_user
from src.lucidpanda.auth.models import User
from src.lucidpanda.infra.cache import get_cached, set_cached
from src.lucidpanda.infra.database.connection import get_session
from src.lucidpanda.models.intelligence import Intelligence, IntelligenceMobileRead
from src.lucidpanda.models.macro_event import MacroEvent
from src.lucidpanda.services.market_terminal_service import market_terminal_service
from src.lucidpanda.core.logger import logger
from src.lucidpanda.utils import v1_prepare_json, format_iso8601
from src.lucidpanda.utils.confidence import calc_confidence_level, calc_confidence_score
from src.lucidpanda.utils.market_calendar import get_market_status

router = APIRouter()


@router.get("/image")
async def proxy_external_image(url: str = Query(..., description="External image URL to proxy")):
    """
    图像穿透代理 (Image Proxy)
    解决国内 iOS 客户端无法直接访问境外媒体（Bloomberg/Reuters等）图片的问题。
    利用 API 容器自带的 HTTP_PROXY (singbox) 将图片拉取并流式返回给客户端。
    """
    import httpx
    
    # 简单的安全校验，防止 SSRF 或滥用
    if not url.startswith("http"):
        raise HTTPException(status_code=400, detail="Invalid image URL")

    # 获取系统级的代理配置（在 docker-compose 中配置的 HTTP_PROXY=http://singbox:7890）
    import os
    proxies = {}
    http_proxy = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")
    https_proxy = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")
    if http_proxy:
        proxies["http://"] = http_proxy
    if https_proxy:
        proxies["https://"] = https_proxy

    async def image_streamer():
        # 使用配置了代理的异步客户端
        async with httpx.AsyncClient(proxies=proxies if proxies else None, verify=False) as client:
            try:
                # 使用 stream 模式，不把整张图吃进内存，边下边传给 iOS
                async with client.stream("GET", url, timeout=10.0) as response:
                    if response.status_code != 200:
                        yield b""
                        return
                    async for chunk in response.aiter_bytes():
                        yield chunk
            except Exception as e:
                import logging
                logging.error(f"Image Proxy failed for {url}: {e}")
                yield b""

    return StreamingResponse(image_streamer(), media_type="image/jpeg")


@router.get("/intelligence/{item_id}/ai_summary", response_model=dict[str, str])
async def get_mobile_intelligence_ai_summary(
    item_id: int, db: Session = Depends(get_session)
):
    """
    Fetch AI summary/actionable advice for a specific intelligence item.
    """
    statement = select(Intelligence).where(Intelligence.id == item_id)
    result = db.exec(statement).first()
    if not result:
        raise HTTPException(status_code=404, detail="Item not found")

    advice_text = "目前没有针对该情报的深度AI分析策略。"
    if isinstance(result.actionable_advice, dict):
        advice_text = (
            result.actionable_advice.get("zh")
            or result.actionable_advice.get("en")
            or advice_text
        )
    elif isinstance(result.actionable_advice, str) and result.actionable_advice.strip():
        advice_text = result.actionable_advice

    return v1_prepare_json({"ai_summary": advice_text})


@router.get("/dashboard/summary", response_model=dict[str, Any])
async def get_mobile_dashboard_summary(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_session)
):
    """
    Production-grade Aggregated Endpoint for Mobile.
    Reduces RTT by combining watchlist, market status, and top alerts.
    """
    return v1_prepare_json(
        {
            "market_status": get_market_status("CN"),
            "watchlist": [],  # List[FundMobileSummary]
            "critical_alerts": [],  # List[IntelligenceMobileRead]
        }
    )


@router.get("/intelligence", response_model=list[IntelligenceMobileRead])
async def get_mobile_intelligence(
    category: str | None = Query(None, description="Optional category filter (e.g. macro_gold)"),
    limit: int = Query(20, ge=1, le=100, description="Max number of items to return"),
    db: Session = Depends(get_session)
):
    """
    Trimmed intelligence feed for mobile.
    Only returns essential fields to save bandwidth.
    """
    statement = (
        select(Intelligence)
        .where(Intelligence.status == "COMPLETED")
        .where(col(Intelligence.summary).is_not(None))
    )
    
    if category:
        statement = statement.where(Intelligence.category == category)
        
    statement = statement.order_by(col(Intelligence.timestamp).desc()).limit(limit)
    results = db.exec(statement).all()

    # Transformation logic from rich JSONB to flat mobile string
    mobile_items = []
    for item in results:
        # Business logic to select the best language for mobile summary
        summary_text = "无摘要"
        if isinstance(item.summary, dict):
            summary_text = (
                item.summary.get("zh")
                or item.summary.get("en")
                or next(
                    (
                        v
                        for v in item.summary.values()
                        if isinstance(v, str) and v.strip()
                    ),
                    "无摘要",
                )
            )
        elif isinstance(item.summary, str) and item.summary.strip():
            summary_text = item.summary

        urgency_score = item.urgency_score if isinstance(item.urgency_score, int) else 0
        timestamp = item.timestamp or datetime.now(UTC)

        sentiment_label = "Neutral"
        if isinstance(item.sentiment, dict):
            sentiment_label = (
                item.sentiment.get("zh") or item.sentiment.get("en") or "Neutral"
            )
        elif isinstance(item.sentiment, str) and item.sentiment.strip():
            sentiment_label = item.sentiment
        content_text = ""
        if isinstance(item.content, dict):
            content_text = (
                item.content.get("zh")
                or item.content.get("en")
                or next(
                    (
                        v
                        for v in item.content.values()
                        if isinstance(v, str) and v.strip()
                    ),
                    "",
                )
            )
        elif isinstance(item.content, str):
            content_text = item.content

        confidence_score = calc_confidence_score(
            item.corroboration_count,
            getattr(item, "source_credibility_score", None),
            item.urgency_score,
            item.timestamp,
        )

        mobile_items.append(
            IntelligenceMobileRead(
                id=item.id,
                timestamp=timestamp,
                author=item.author or "Unknown",
                summary=str(summary_text),
                content=str(content_text),
                image_url=getattr(item, "image_url", None),
                urgency_score=urgency_score,
                sentiment_label=sentiment_label,
                gold_price_snapshot=item.gold_price_snapshot,
                dxy_snapshot=item.dxy_snapshot,
                us10y_snapshot=item.us10y_snapshot,
                oil_snapshot=None,  # 如果需要可以添加
                price_15m=item.price_15m,
                price_1h=item.price_1h,
                price_4h=item.price_4h,
                price_12h=item.price_12h,
                price_24h=item.price_24h,
                corroboration_count=item.corroboration_count or 1,
                confidence_score=confidence_score,
                confidence_level=calc_confidence_level(confidence_score),
            )
        )
    return v1_prepare_json(mobile_items)


@router.get("/market/snapshot", response_model=dict[str, Any])
async def get_mobile_market_snapshot():
    """
    Fetch real-time market snapshot for iOS terminal.
    Includes: Gold, DXY, Crude Oil, US10Y Treasury.
    """
    snapshot = market_terminal_service.get_market_snapshot()
    if not snapshot:
        raise HTTPException(
            status_code=503, detail="Market data temporarily unavailable"
        )
    return v1_prepare_json(snapshot)


@router.get("/market/pulse", response_model=dict[str, Any])
async def get_market_pulse(
    db: Session = Depends(get_session),
):
    """
    宏观市场脉搏 — 为悬浮胶囊提供聚合数据。
    返回：多品种快照 + 近24h高紧急度情报摘要 + 整体市场情绪 + 趋势图 + 宏观事件
    缓存：15s 全局 Redis 缓存（非个人化数据）
    """
    _CACHE_KEY = "api:market:pulse"
    _CACHE_TTL = 15  # 秒

    cached = get_cached(_CACHE_KEY)
    if cached is not None:
        return cached

    # 核心脉搏计算逻辑
    pulse_data = await _calculate_market_pulse(db)
    
    set_cached(_CACHE_KEY, pulse_data, _CACHE_TTL)
    return pulse_data

@router.get("/market/pulse/stream")
async def market_pulse_stream(
    db: Session = Depends(get_session),
):
    """
    SSE 流：实时推送市场脉搏数据 (用于 iOS 极速跳动)。
    """
    from sse_starlette.sse import EventSourceResponse
    import asyncio

    async def event_generator():
        while True:
            try:
                pulse_data = await _calculate_market_pulse(db)
                yield {
                    "data": json.dumps(v1_prepare_json(pulse_data))
                }
                # 每 10 秒推送一次，平衡性能与实时性
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Market SSE Error: {e}")
                break

    return EventSourceResponse(event_generator())

async def _calculate_market_pulse(db: Session) -> dict[str, Any]:
    """核心脉搏计算逻辑：聚合快照、情报、情绪及事件"""
    def normalize_summary_text(summary_val: Any) -> str:
        if isinstance(summary_val, dict):
            zh = summary_val.get("zh")
            en = summary_val.get("en")
            if isinstance(zh, str) and zh.strip():
                return zh
            if isinstance(en, str) and en.strip():
                return en
            for value in summary_val.values():
                if isinstance(value, str) and value.strip():
                    return value
            return "无摘要"

        if isinstance(summary_val, str):
            text_val = summary_val.strip()
            if text_val.startswith("{"):
                try:
                    parsed = json.loads(text_val)
                    return normalize_summary_text(parsed)
                except Exception:
                    return text_val or "无摘要"
            return text_val or "无摘要"

        if summary_val is None:
            return "无摘要"

        return str(summary_val)

    now_dt = datetime.now(UTC)
    since_24h = now_dt - timedelta(hours=24)

    # 1. 市场快照
    snapshot = market_terminal_service.get_market_snapshot()

    # 2. 近24h高紧急度情报 (urgency_score >= 7)
    top_alerts_raw = (
        db.execute(
            text("""
            SELECT id, timestamp, urgency_score, summary, sentiment_score
            FROM intelligence
            WHERE timestamp >= :since AND urgency_score >= 7 AND status = 'COMPLETED'
            ORDER BY timestamp DESC
            LIMIT 5
            """),
            {"since": since_24h},
        ).mappings().all()
    )
    
    top_alerts = []
    for row in top_alerts_raw:
        summary_text = normalize_summary_text(row["summary"])
        row_timestamp = row["timestamp"]
        if isinstance(row_timestamp, str):
            try:
                row_timestamp = datetime.fromisoformat(row_timestamp.replace("Z", "+00:00"))
            except ValueError:
                row_timestamp = None

        top_alerts.append({
            "id": row["id"],
            "timestamp": format_iso8601(row_timestamp),
            "urgency_score": row["urgency_score"],
            "summary": summary_text,
            "sentiment": "bullish" if row["sentiment_score"] > 0.15 else ("bearish" if row["sentiment_score"] < -0.15 else "neutral")
        })

    # 3. 汇总整体情绪
    sentiment_stats = db.execute(
        text("SELECT AVG(sentiment_score) as avg_score, COUNT(*) as total FROM intelligence WHERE timestamp >= :since AND status = 'COMPLETED'"),
        {"since": since_24h}
    ).mappings().first()
    
    avg_sentiment = sentiment_stats["avg_score"] or 0.0
    alert_count = sentiment_stats["total"] or 0

    # 4. 情绪走势 (Sparkline 支持)
    trend_raw = db.execute(
        text("""
            SELECT date_trunc('hour', timestamp) AS hour, AVG(sentiment_score) AS avg_score
            FROM intelligence
            WHERE timestamp >= :since AND status = 'COMPLETED'
            GROUP BY 1 ORDER BY 1 ASC
        """),
        {"since": since_24h},
    ).mappings().all()

    trend_map = {row["hour"]: round(float(row["avg_score"]), 3) for row in trend_raw}
    sentiment_trend = []
    start_hour = now_dt.replace(minute=0, second=0, microsecond=0) - timedelta(hours=24)
    for i in range(25):
        current_h = start_hour + timedelta(hours=i)
        sentiment_trend.append({
            "hour": format_iso8601(current_h),
            "score": trend_map.get(current_h, 0.0)
        })

    # 5. 未来 48h 宏观事件
    until_dt = now_dt + timedelta(hours=48)
    try:
        upcoming_events_raw = db.exec(
            select(MacroEvent)
            .where(col(MacroEvent.release_date) >= now_dt.date())
            .where(col(MacroEvent.release_date) <= until_dt.date())
            .where(col(MacroEvent.impact_level).in_(["high", "medium"]))
            .order_by(col(MacroEvent.release_date).asc(), col(MacroEvent.release_time).asc())
            .limit(5)
        ).all()
    except Exception as e:
        logger.error(f"Failed to fetch macro events: {e}")
        upcoming_events_raw = []

    upcoming_events = [{
        "id": str(event.id),
        "title": event.title,
        "country": event.country,
        "date": event.release_date.isoformat(),
        "time": event.release_time,
        "impact": event.impact_level,
        "forecast": event.forecast_value,
        "previous": event.previous_value,
    } for event in upcoming_events_raw]

    return {
        "market_snapshot": snapshot,
        "top_alerts": top_alerts,
        "upcoming_events": upcoming_events,
        "overall_sentiment": "bullish" if avg_sentiment > 0.15 else ("bearish" if avg_sentiment < -0.15 else "neutral"),
        "overall_sentiment_zh": "看多" if avg_sentiment > 0.15 else ("看空" if avg_sentiment < -0.15 else "中性"),
        "sentiment_score": round(avg_sentiment, 3),
        "sentiment_trend": sentiment_trend,
        "alert_count_24h": alert_count,
        "generated_at": format_iso8601(datetime.now(UTC))
    }


@router.get("/discover", response_model=dict[str, Any])
async def get_mobile_discover(db: Session = Depends(get_session)):
    """
    Discovery feed for mobile.
    Returns trending fund tags and suggested readings.
    """
    # 1. Trending Tags (Backend-curated or analytics-driven)
    # In a real app, this might come from a 'trending' table or cache.
    trending_tags = [
        {"title": "博时黄金", "code": "159937"},
        {"title": "华安黄金", "code": "518880"},
        {"title": "易方达黄金", "code": "161128"},
        {"title": "沪深300", "code": "510300"},
        {"title": "纳指100", "code": "513100"},
    ]

    # 2. Suggested Reading (High-urgency intelligence items)
    statement = (
        select(Intelligence)
        .where(Intelligence.status == "COMPLETED")
        .where(Intelligence.urgency_score >= 8)
        .order_by(col(Intelligence.timestamp).desc())
        .limit(3)
    )
    results = db.exec(statement).all()

    suggested_reading = []
    for item in results:
        # Resolve best summary text
        summary_text = "分析中..."
        if isinstance(item.summary, dict):
            summary_text = item.summary.get("zh") or item.summary.get("en") or summary_text
        elif isinstance(item.summary, str):
            summary_text = item.summary

        # Resolve category (mocking for now based on actual intelligence category)
        category_key = "funds.discover.category.market_analysis"
        if item.category == "macro_gold":
            category_key = "funds.discover.category.economy"

        # Mock image URLs based on ID or category
        image_url = f"https://picsum.photos/seed/{item.id}/400/400"

        suggested_reading.append({
            "id": item.id,
            "category_key": category_key,
            "title": summary_text,
            "timestamp": item.timestamp.isoformat(),
            "imageUrl": image_url
        })

    return v1_prepare_json({
        "trending_tags": trending_tags,
        "suggested_reading": suggested_reading
    })
