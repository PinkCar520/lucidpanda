from datetime import UTC, datetime
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Column, Field, SQLModel


class IntelligenceBase(SQLModel):
    source_id: str | None = Field(default=None, unique=True)
    source_name: str | None = None
    event_cluster_id: str | None = Field(default=None, index=True)
    author: str | None = None
    content: str | None = None
    urgency_score: int | None = 0
    url: str | None = None
    category: str = Field(
        default="macro_gold", index=True
    )  # macro_gold | equity_cn | equity_us
    image_url: str | None = None
    local_image_path: str | None = None

    # Complex fields using JSONB for performance and Web requirements
    summary: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    sentiment: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))
    market_implication: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    actionable_advice: dict[str, Any] | None = Field(
        default=None, sa_column=Column(JSONB)
    )
    entities: Any | None = Field(default=None, sa_column=Column(JSONB))
    tags: list[dict[str, Any]] | None = Field(default=None, sa_column=Column(JSONB))
    relation_triples: Any | None = Field(default=None, sa_column=Column(JSONB))
    agent_trace: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB))

    gold_price_snapshot: float | None = None
    price_15m: float | None = None
    price_1h: float | None = None
    price_4h: float | None = None
    price_12h: float | None = None
    price_24h: float | None = None
    market_session: str | None = None
    clustering_score: int = 0
    exhaustion_score: float = 0.0
    dxy_snapshot: float | None = None
    us10y_snapshot: float | None = None
    gvz_snapshot: float | None = None
    corroboration_count: int = 1
    source_credibility_score: float | None = None
    alpha_return: float | None = None
    expectation_gap: float | None = None
    sentiment_score: float | None = Field(default=0.0, index=True)


class Intelligence(IntelligenceBase, table=True):
    __tablename__ = "intelligence"
    id: int | None = Field(default=None, primary_key=True)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str | None = Field(default="PENDING", index=True)
    last_error: str | None = None


class IntelligenceRead(IntelligenceBase):
    id: int
    timestamp: datetime


# iOS Specific Summary DTO
class IntelligenceMobileRead(SQLModel):
    id: int
    timestamp: datetime
    author: str
    summary: str  # Flattened for mobile
    content: str  # Full content for peek sheet
    image_url: str | None = None
    local_image_path: str | None = None
    urgency_score: int
    sentiment_label: str  # Derived for mobile
    gold_price_snapshot: float | None = None
    dxy_snapshot: float | None = None
    us10y_snapshot: float | None = None
    oil_snapshot: float | None = None
    price_15m: float | None = None
    price_1h: float | None = None
    price_4h: float | None = None
    price_12h: float | None = None
    price_24h: float | None = None
    corroboration_count: int = 1
    confidence_score: float = 0.0
    confidence_level: str = "LOW"
    alpha_return: float | None = None
    expectation_gap: float | None = None
