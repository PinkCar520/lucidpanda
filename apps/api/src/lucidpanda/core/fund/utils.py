import logging
from datetime import datetime
from typing import Any

from src.lucidpanda.utils.market_calendar import (
    get_market_status,
)

logger = logging.getLogger(__name__)


def safe_fee_rate(value: Any) -> float:
    """Normalize a fee value into annual percentage (e.g. 1.2 => 1.2%)."""
    try:
        if value is None:
            return 0.0
        return max(0.0, float(value))
    except Exception:
        return 0.0


def infer_market_region_from_meta(fund_code: str, meta: dict[str, Any] | None = None, fallback_name: str = "") -> str:
    """Heuristic to infer market region (CN/HK/US) from fund metadata."""
    meta = meta or {}
    fund_name = str(meta.get('name') or fallback_name or "")
    fund_type = str(meta.get('type') or "")
    if "QDII" not in fund_type and "QDII" not in fund_name:
        return "CN"
    if any(k in fund_name for k in ["恒生", "港", "HK", "H股"]):
        return "HK"
    return "US"


def get_market_day_progress(region: str, now_utc: datetime | None = None) -> float:
    """Return elapsed fraction [0, 1] for the current trading day."""
    import pytz

    # Use timezone-aware UTC now to avoid deprecation warnings
    from datetime import timezone
    now_utc = now_utc or datetime.now(timezone.utc)
    
    if now_utc.tzinfo is None:
        now_utc = pytz.utc.localize(now_utc)
    else:
        now_utc = now_utc.astimezone(pytz.utc)

    if region == "HK":
        tz = pytz.timezone("Asia/Hong_Kong")
        sessions = [((9, 30), (12, 0)), ((13, 0), (16, 0))]
    elif region == "US":
        tz = pytz.timezone("America/New_York")
        sessions = [((9, 30), (16, 0))]
    else:
        tz = pytz.timezone("Asia/Shanghai")
        sessions = [((9, 30), (11, 30)), ((13, 0), (15, 0))]

    now_local = now_utc.astimezone(tz)
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    elapsed_minutes = 0.0
    total_minutes = 0.0
    for (sh, sm), (eh, em) in sessions:
        start = day_start.replace(hour=sh, minute=sm)
        end = day_start.replace(hour=eh, minute=em)
        span = max(0.0, (end - start).total_seconds() / 60.0)
        total_minutes += span
        if now_local <= start:
            continue
        if now_local >= end:
            elapsed_minutes += span
        else:
            elapsed_minutes += max(0.0, (now_local - start).total_seconds() / 60.0)

    if total_minutes <= 0:
        return 1.0
    return max(0.0, min(1.0, elapsed_minutes / total_minutes))


def calculate_fee_drag_pct(
    fund_code: str,
    db: Any,  # IntelligenceDB instance
    fund_meta: dict[str, Any] | None = None,
    fund_name: str = ""
) -> tuple[float, float, float, float, dict[str, float]]:
    """
    Convert annual fee rates to daily drag.
    Returns: (applied_drag_pct, annual_total_pct, daily_fee_pct, day_progress, breakdown)
    """
    fund_meta = fund_meta or {}

    mgmt = safe_fee_rate(fund_meta.get("mgmt_fee_rate"))
    custody = safe_fee_rate(fund_meta.get("custodian_fee_rate"))
    sales = safe_fee_rate(fund_meta.get("sales_fee_rate"))

    # Fallback to DB snapshot if not preloaded in metadata
    if mgmt == 0.0 and custody == 0.0 and sales == 0.0:
        stats_map = db.get_fund_stats([fund_code]) or {}
        stats = stats_map.get(fund_code, {})
        mgmt = safe_fee_rate(stats.get("mgmt_fee_rate"))
        custody = safe_fee_rate(stats.get("custodian_fee_rate"))
        sales = safe_fee_rate(stats.get("sales_fee_rate"))

    annual_total_pct = mgmt + custody + sales
    if annual_total_pct <= 0:
        return 0.0, 0.0, 0.0, 0.0, {"mgmt": mgmt, "custody": custody, "sales": sales}

    # Precise annual -> daily conversion using compounding base.
    daily_fee_pct = ((1.0 + annual_total_pct / 100.0) ** (1.0 / 365.0) - 1.0) * 100.0

    region = infer_market_region_from_meta(fund_code, fund_meta, fund_name)
    market_status = get_market_status(region)
    if market_status == "closed":
        day_progress = 1.0
    else:
        day_progress = get_market_day_progress(region)

    applied_drag_pct = daily_fee_pct * day_progress
    return applied_drag_pct, annual_total_pct, daily_fee_pct, day_progress, {
        "mgmt": mgmt,
        "custody": custody,
        "sales": sales
    }
