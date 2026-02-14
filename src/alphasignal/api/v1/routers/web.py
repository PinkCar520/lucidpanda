from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from typing import List, Dict, Any
from src.alphasignal.infra.database.connection import get_session
from src.alphasignal.models.fund import FundMetadata, FundValuationArchive
from src.alphasignal.models.intelligence import Intelligence

router = APIRouter()

@router.get("/funds/matrix", response_model=List[Dict[str, Any]])
async def get_web_fund_matrix(
    db: Session = Depends(get_session)
):
    """
    High-density data matrix for Web dashboard.
    Returns full actuarial dimensions.
    """
    # Optimized query for web density
    statement = select(FundMetadata).limit(100)
    results = db.exec(statement).all()
    return [item.model_dump() for item in results]

@router.get("/intelligence/full", response_model=List[Intelligence])
async def get_web_intelligence_full(
    limit: int = 50,
    db: Session = Depends(get_session)
):
    """
    Returns full rich JSONB objects for Web localized rendering.
    """
    statement = select(Intelligence).order_by(Intelligence.timestamp.desc()).limit(limit)
    return db.exec(statement).all()
