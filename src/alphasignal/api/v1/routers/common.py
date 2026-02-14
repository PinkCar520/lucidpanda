from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from typing import Dict, Any
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.intelligence import Intelligence
from datetime import datetime, timedelta

router = APIRouter()

@router.get("/alerts/24h", response_model=Dict[str, Any])
async def get_24h_alerts_count(
    db: Session = Depends(get_session)
):
    """
    Get the count of high-urgency (score 8+) alerts in the last 24 hours.
    Shared by both Web and Mobile.
    """
    # SQLModel approach
    threshold_time = datetime.utcnow() - timedelta(hours=24)
    statement = select(func.count(Intelligence.id)).where(
        Intelligence.urgency_score >= 8,
        Intelligence.timestamp > threshold_time
    )
    count = db.exec(statement).first() or 0
    
    return {"count": count}
