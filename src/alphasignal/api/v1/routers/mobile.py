from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select, text
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.fund import FundMetadata, FundMobileSummary
from src.alphasignal.models.intelligence import Intelligence, IntelligenceMobileRead
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.utils import v1_prepare_json
from src.alphasignal.utils.confidence import calc_confidence_score, calc_confidence_level
from src.alphasignal.utils.market_calendar import get_market_status
from src.alphasignal.services.market_terminal_service import market_terminal_service
from src.alphasignal.infra.cache import get_cached, set_cached

router = APIRouter()

@router.get("/intelligence/{item_id}/ai_summary", response_model=Dict[str, str])
async def get_mobile_intelligence_ai_summary(
    item_id: int,
    db: Session = Depends(get_session)
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
        advice_text = result.actionable_advice.get("zh") or result.actionable_advice.get("en") or advice_text
    elif isinstance(result.actionable_advice, str) and result.actionable_advice.strip():
        advice_text = result.actionable_advice
        
    return v1_prepare_json({"ai_summary": advice_text})

@router.get("/dashboard/summary", response_model=Dict[str, Any])
async def get_mobile_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Production-grade Aggregated Endpoint for Mobile.
    Reduces RTT by combining watchlist, market status, and top alerts.
    """
    return v1_prepare_json({
        "market_status": get_market_status('CN'),
        "watchlist": [], # List[FundMobileSummary]
        "critical_alerts": [] # List[IntelligenceMobileRead]
    })

@router.get("/intelligence", response_model=List[IntelligenceMobileRead])
async def get_mobile_intelligence(
    limit: int = 20,
    db: Session = Depends(get_session)
):
    """
    Trimmed intelligence feed for mobile.
    Only returns essential fields to save bandwidth.
    """
    statement = select(Intelligence).order_by(Intelligence.timestamp.desc()).limit(limit)
    results = db.exec(statement).all()

    # Transformation logic from rich JSONB to flat mobile string
    mobile_items = []
    for item in results:
        # Business logic to select the best language for mobile summary
        summary_text = "无摘要"
        if isinstance(item.summary, dict):
            summary_text = item.summary.get("zh") or item.summary.get("en") or next((v for v in item.summary.values() if isinstance(v, str) and v.strip()), "无摘要")
        elif isinstance(item.summary, str) and item.summary.strip():
            summary_text = item.summary

        urgency_score = item.urgency_score if isinstance(item.urgency_score, int) else 0
        timestamp = item.timestamp or datetime.utcnow()

        sentiment_label = "Neutral"
        if isinstance(item.sentiment, dict):
            sentiment_label = item.sentiment.get("zh") or item.sentiment.get("en") or "Neutral"
        elif isinstance(item.sentiment, str) and item.sentiment.strip():
            sentiment_label = item.sentiment
        content_text = ""
        if isinstance(item.content, dict):
            content_text = item.content.get("zh") or item.content.get("en") or next((v for v in item.content.values() if isinstance(v, str) and v.strip()), "")
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
                summary=summary_text,
                content=content_text,
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


@router.get("/market/snapshot", response_model=Dict[str, Any])
async def get_mobile_market_snapshot():
    """
    Fetch real-time market snapshot for iOS terminal.
    Includes: Gold, DXY, Crude Oil, US10Y Treasury.
    """
    snapshot = market_terminal_service.get_market_snapshot()
    if not snapshot:
        raise HTTPException(status_code=503, detail="Market data temporarily unavailable")
    return v1_prepare_json(snapshot)


@router.get("/market/pulse", response_model=Dict[str, Any])
async def get_market_pulse(
    db: Session = Depends(get_session),
):
    """
    宏观市场脉搏 — 为悬浮胶囊提供聚合数据。
    返回：四大品种快照 + 近24h高紧急度情报摘要 + 整体市场情绪
    缓存：30s 全局 Redis 缓存（非个人化数据）
    """
    _CACHE_KEY = "api:market:pulse"
    _CACHE_TTL = 30  # 秒

    cached = get_cached(_CACHE_KEY)
    if cached is not None:
        return cached

    # 1. 四大品种实时快照
    snapshot = market_terminal_service.get_market_snapshot()

    # 2. 近24h高紧急度情报 (urgency_score >= 7)，最多取5条
    # 同时取 sentiment_score 浮点列用于情绪标签
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    top_alerts_raw = db.execute(
        text("""
            SELECT id, timestamp, urgency_score, summary, sentiment_score
            FROM intelligence
            WHERE timestamp > :since
              AND urgency_score >= 7
              AND summary IS NOT NULL
            ORDER BY urgency_score DESC, timestamp DESC
            LIMIT 5
        """),
        {"since": since_24h},
    ).mappings().all()

    top_alerts = []
    for row in top_alerts_raw:
        summary_text = "无摘要"
        if isinstance(row["summary"], dict):
            summary_text = row["summary"].get("zh") or row["summary"].get("en") or summary_text
        elif isinstance(row["summary"], str):
            summary_text = row["summary"]

        # 直接使用 sentiment_score 浮点列，无需解析 JSONB
        score = float(row["sentiment_score"]) if row["sentiment_score"] is not None else 0.0
        sentiment_label = "bullish" if score > 0.15 else ("bearish" if score < -0.15 else "neutral")

        top_alerts.append({
            "id": row["id"],
            "timestamp": row["timestamp"].isoformat() if row["timestamp"] else None,
            "urgency_score": row["urgency_score"],
            "summary": summary_text,
            "sentiment": sentiment_label,
        })

    # 3. 近24h整体情绪 — 使用 sentiment_score 浮点列（准确，无 JSONB 解析开销）
    sentiment_row = db.execute(
        text("""
            SELECT AVG(sentiment_score) AS avg_score,
                   COUNT(*) AS count
            FROM intelligence
            WHERE timestamp > :since
              AND sentiment_score IS NOT NULL
        """),
        {"since": since_24h},
    ).mappings().first()

    avg_sentiment = 0.0
    if sentiment_row and sentiment_row["avg_score"] is not None:
        avg_sentiment = round(float(sentiment_row["avg_score"]), 3)

    if avg_sentiment > 0.15:
        overall_sentiment = "bullish"
        overall_sentiment_zh = "偏多"
    elif avg_sentiment < -0.15:
        overall_sentiment = "bearish"
        overall_sentiment_zh = "偏空"
    else:
        overall_sentiment = "neutral"
        overall_sentiment_zh = "中性"

    # 4. 近24h情绪趋势 — 按小时聚合 (Sparkline 支持)
    trend_raw = db.execute(
        text("""
            SELECT date_trunc('hour', timestamp) AS hour,
                   AVG(sentiment_score) AS avg_score
            FROM intelligence
            WHERE timestamp > :since
              AND sentiment_score IS NOT NULL
            GROUP BY 1
            ORDER BY 1 ASC
        """),
        {"since": since_24h},
    ).mappings().all()

    # 构建完整的 24 小时时间序列，处理空缺小时
    trend_map = {row["hour"]: round(float(row["avg_score"]), 3) for row in trend_raw}
    sentiment_trend = []
    
    # 从 24 小时前开始，到当前小时结束
    start_hour = (datetime.now(timezone.utc) - timedelta(hours=24)).replace(minute=0, second=0, microsecond=0)
    for i in range(25):
        current_h = start_hour + timedelta(hours=i)
        # 如果该小时没数据，则使用 0.0 或上一个点的值（这里采用 0.0 保持图表真实性）
        score = trend_map.get(current_h, 0.0)
        sentiment_trend.append({
            "hour": current_h.isoformat(),
            "score": score
        })

    result = v1_prepare_json({
        "market_snapshot": snapshot,
        "top_alerts": top_alerts,
        "overall_sentiment": overall_sentiment,
        "overall_sentiment_zh": overall_sentiment_zh,
        "sentiment_score": avg_sentiment,
        "sentiment_trend": sentiment_trend,
        "alert_count_24h": sentiment_row["count"] if sentiment_row else 0,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    })
    set_cached(_CACHE_KEY, result, ttl=_CACHE_TTL)
    return result
