from typing import Optional, List, Dict, Any
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Column
from sqlalchemy.dialects.postgresql import JSONB

class FundMetadataBase(SQLModel):
    fund_code: str = Field(primary_key=True)
    fund_name: str
    full_name: Optional[str] = None
    pinyin_shorthand: Optional[str] = None
    investment_type: Optional[str] = None
    style_tag: Optional[str] = None
    risk_level: Optional[str] = None
    inception_date: Optional[date] = None
    listing_status: str = "L"
    currency: str = "CNY"
    benchmark_text: Optional[str] = None

class FundMetadata(FundMetadataBase, table=True):
    __tablename__ = "fund_metadata"
    last_full_sync: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class FundValuationArchive(SQLModel, table=True):
    __tablename__ = "fund_valuation_archive"
    id: Optional[int] = Field(default=None, primary_key=True)
    trade_date: date
    fund_code: str
    frozen_est_growth: Optional[float] = None
    frozen_components: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    frozen_sector_attribution: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSONB))
    official_growth: Optional[float] = None
    deviation: Optional[float] = None
    tracking_status: Optional[str] = None
    applied_bias_offset: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Mobile Optimized DTO
class FundMobileSummary(SQLModel):
    fund_code: str
    fund_name: str
    estimated_growth: float
    urgency_level: str # Derived: 'normal' | 'warning' | 'critical'
    confidence_score: int
    risk_level: str
