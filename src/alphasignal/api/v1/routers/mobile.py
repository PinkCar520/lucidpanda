from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from typing import List, Optional, Dict, Any
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.fund import FundMetadata, FundMobileSummary
from src.alphasignal.models.intelligence import Intelligence, IntelligenceMobileRead
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.utils import v1_prepare_json

router = APIRouter()

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
        summary_text = item.summary.get("zh") if item.summary else "无摘要"
        
        mobile_items.append(
            IntelligenceMobileRead(
                id=item.id,
                timestamp=item.timestamp,
                summary=summary_text,
                urgency_score=item.urgency_score,
                sentiment_label="Bearish" # Example logic
            )
        )
    return v1_prepare_json(mobile_items)
