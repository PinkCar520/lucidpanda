from datetime import date, datetime
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class MacroEvent(SQLModel, table=True):
    __tablename__ = "macro_event"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    event_code: str = Field(index=True)
    release_date: date = Field(index=True)
    release_time: str | None = None
    country: str
    title: str
    impact_level: str

    previous_value: str | None = None
    forecast_value: str | None = None
    actual_value: str | None = None

    source: str
    updated_at: datetime = Field(default_factory=datetime.utcnow)
