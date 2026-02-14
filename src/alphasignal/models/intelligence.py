from typing import Optional, Dict, Any
from datetime import datetime
from sqlmodel import SQLModel, Field, Column, JSON
from sqlalchemy.dialects.postgresql import JSONB

class IntelligenceBase(SQLModel):
    source_id: Optional[str] = Field(default=None, unique=True)
    author: Optional[str] = None
    content: Optional[str] = None
    urgency_score: Optional[int] = 0
    url: Optional[str] = None
    
    # Complex fields using JSONB for performance and Web requirements
    summary: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    sentiment: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    market_implication: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    actionable_advice: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))

    gold_price_snapshot: Optional[float] = None
    price_15m: Optional[float] = None
    price_1h: Optional[float] = None
    price_4h: Optional[float] = None
    price_12h: Optional[float] = None
    price_24h: Optional[float] = None
    market_session: Optional[str] = None
    clustering_score: int = 0
    exhaustion_score: float = 0.0
    dxy_snapshot: Optional[float] = None
    us10y_snapshot: Optional[float] = None
    gvz_snapshot: Optional[float] = None

class Intelligence(IntelligenceBase, table=True):
    __tablename__ = "intelligence"
    id: Optional[int] = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class IntelligenceRead(IntelligenceBase):
    id: int
    timestamp: datetime

# iOS Specific Summary DTO
class IntelligenceMobileRead(SQLModel):
    id: int
    timestamp: datetime
    summary: str  # Flattened for mobile
    urgency_score: int
    sentiment_label: str # Derived for mobile
