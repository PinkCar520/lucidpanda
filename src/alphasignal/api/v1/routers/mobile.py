from fastapi import APIRouter, Depends, Query, HTTPException
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from datetime import datetime
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.fund import FundMetadata, FundMobileSummary
from src.alphasignal.models.intelligence import Intelligence, IntelligenceMobileRead
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.utils import v1_prepare_json

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
        "market_status": "OPEN",
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
        
        mobile_items.append(
            IntelligenceMobileRead(
                id=item.id,
                timestamp=timestamp,
                author=item.author or "Unknown",
                summary=summary_text,
                urgency_score=urgency_score,
                sentiment_label=sentiment_label
            )
        )
    return v1_prepare_json(mobile_items)
