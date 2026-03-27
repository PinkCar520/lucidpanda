from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class FundMetadataBase(SQLModel):
    fund_code: str = Field(primary_key=True)
    fund_name: str
    full_name: str | None = None
    pinyin_shorthand: str | None = None
    investment_type: str | None = None
    style_tag: str | None = None
    risk_level: str | None = None
    inception_date: date | None = None
    listing_status: str = "L"
    currency: str = "CNY"
    benchmark_text: str | None = None


class FundMetadata(FundMetadataBase, table=True):
    __tablename__ = "fund_metadata"
    last_full_sync: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class FundValuationArchive(SQLModel, table=True):
    __tablename__ = "fund_valuation_archive"
    id: int | None = Field(default=None, primary_key=True)
    trade_date: date
    fund_code: str
    frozen_est_growth: float | None = None
    frozen_components: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    frozen_sector_attribution: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    official_growth: float | None = None
    deviation: float | None = None
    tracking_status: str | None = None
    applied_bias_offset: float = 0.0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# Mobile Optimized DTO
class FundMobileSummary(SQLModel):
    fund_code: str
    fund_name: str
    estimated_growth: float
    urgency_level: str  # Derived: 'normal' | 'warning' | 'critical'
    confidence_score: int
    risk_level: str
