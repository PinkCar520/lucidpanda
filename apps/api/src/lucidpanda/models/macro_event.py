from uuid import UUID, uuid4
from datetime import date, datetime
from typing import Optional
from sqlmodel import SQLModel, Field

class MacroEvent(SQLModel, table=True):
    __tablename__ = "macro_event"
    
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_code: str = Field(index=True)
    release_date: date = Field(index=True)
    release_time: Optional[str] = None
    country: str
    title: str
    impact_level: str
    
    previous_value: Optional[str] = None
    forecast_value: Optional[str] = None
    actual_value: Optional[str] = None
    
    source: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
