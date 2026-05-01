from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.engine.row import RowMapping


def format_iso8601(dt: datetime) -> str | None:
    """Standardize date string for iOS/Web compatibility.
    Always converts to UTC before adding 'Z' suffix if dt is timezone-aware.
    """
    if not dt:
        return None
    
    # Convert to UTC if it has timezone info
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
        
    # Ensure it's formatted as YYYY-MM-DDTHH:mm:ss.sssZ
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:23] + "Z"


def v1_prepare_json(obj):
    """Recursively prepare object for V1 JSON serialization."""
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, date)):
        if isinstance(obj, datetime):
            return format_iso8601(obj)
        return obj.isoformat()
    if isinstance(obj, RowMapping):
        return {k: v1_prepare_json(v) for k, v in obj.items()}
    if isinstance(obj, dict):
        return {k: v1_prepare_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [v1_prepare_json(i) for i in obj]
    if isinstance(obj, (bytes, memoryview)):
        return None  # Binaries should not be sent in JSON
    if hasattr(obj, "__dict__"):
        # For SQLModel/Pydantic objects not yet serialized
        return {
            k: v1_prepare_json(v)
            for k, v in obj.__dict__.items()
            if not k.startswith("_")
        }
    return obj
