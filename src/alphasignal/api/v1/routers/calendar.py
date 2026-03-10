from fastapi import APIRouter, Depends, Query
from typing import List, Optional, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel
from sqlmodel import Session, text
import asyncio
from src.alphasignal.auth.dependencies import get_current_user
from src.alphasignal.auth.models import User
from src.alphasignal.infra.database.connection import get_session

try:
    import pandas as pd  # type: ignore
except Exception:  # pragma: no cover
    pd = None

router = APIRouter(prefix="/calendar", tags=["calendar"])

# ==================== DTOs ====================

class CalendarEventSchema(BaseModel):
    id: str
    date: str           # "YYYY-MM-DD"
    time: Optional[str] = None   # "HH:MM" or None (all-day)
    type: str           # earnings | dividend | ipo | economic | announcement
    title: str
    description: Optional[str] = None
    impact: str         # high | medium | low
    related_symbols: List[str] = []
    is_watchlist_related: bool = False

class CalendarResponse(BaseModel):
    events: List[CalendarEventSchema]
    date_range: Dict[str, str]

# ==================== Data Sources (P2) ====================

def _get_user_watchlist_codes(current_user: User, db: Session, limit: int = 50) -> List[str]:
    rows = db.execute(
        text(
            """
            SELECT fund_code
            FROM fund_watchlist
            WHERE user_id = :user_id AND is_deleted = FALSE
            ORDER BY sort_index ASC
            LIMIT :limit
            """
        ),
        {"user_id": str(current_user.id), "limit": limit},
    ).fetchall()
    return [r[0] for r in rows if r and r[0]]


def _date_in_window(d: date, date_from: date, date_to: date) -> bool:
    return date_from <= d <= date_to


def _as_date(value: Any) -> Optional[date]:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    # pandas Timestamp
    if hasattr(value, "to_pydatetime"):
        try:
            return value.to_pydatetime().date()
        except Exception:
            return None
    # string
    if isinstance(value, str):
        try:
            return date.fromisoformat(value[:10])
        except Exception:
            return None
    return None


def _extract_yfinance_calendar_dates(cal_df: Any) -> Dict[str, date]:
    """
    yfinance `Ticker.calendar` format is not stable; normalize a few known fields.
    Returns mapping: {"earnings": date, "ex_dividend": date}
    """
    if cal_df is None:
        return {}
    if pd is not None and isinstance(cal_df, pd.DataFrame) and cal_df.empty:
        return {}

    result: Dict[str, date] = {}

    try:
        if pd is not None and isinstance(cal_df, pd.DataFrame):
            # Common format: index = event name, single column.
            # Try a couple of access paths.
            for key, out_key in [
                ("Earnings Date", "earnings"),
                ("Ex-Dividend Date", "ex_dividend"),
            ]:
                if key in getattr(cal_df, "index", []):
                    raw = cal_df.loc[key]
                    if pd is not None and isinstance(raw, pd.Series):
                        value = raw.iloc[0] if len(raw) else None
                    else:
                        value = raw
                    d = _as_date(value)
                    if d:
                        result[out_key] = d
                elif key in getattr(cal_df, "columns", []):
                    d = _as_date(cal_df[key].iloc[0] if len(cal_df[key]) else None)
                    if d:
                        result[out_key] = d
    except Exception:
        return result

    return result


def _fetch_single_symbol_events(sym: str, date_from: date, date_to: date) -> List[CalendarEventSchema]:
    """
    Synchronous per-symbol fetch — runs inside run_in_executor.
    Safe to call from a thread.
    """
    try:
        import yfinance as yf  # type: ignore
    except Exception:
        return []

    sym = (sym or "").strip().upper()
    if not sym:
        return []

    events: List[CalendarEventSchema] = []
    try:
        ticker = yf.Ticker(sym)
        cal = getattr(ticker, "calendar", None)
        dates = _extract_yfinance_calendar_dates(cal)
    except Exception:
        return []

    earnings_date = dates.get("earnings")
    if earnings_date and _date_in_window(earnings_date, date_from, date_to):
        ds = earnings_date.strftime("%Y-%m-%d")
        events.append(
            CalendarEventSchema(
                id=f"yf-{sym}-earnings-{ds}",
                date=ds,
                time=None,
                type="earnings",
                title=f"{sym} Earnings",
                description="Source: yfinance",
                impact="medium",
                related_symbols=[sym],
                is_watchlist_related=True,
            )
        )

    ex_div_date = dates.get("ex_dividend")
    if ex_div_date and _date_in_window(ex_div_date, date_from, date_to):
        ds = ex_div_date.strftime("%Y-%m-%d")
        events.append(
            CalendarEventSchema(
                id=f"yf-{sym}-exdiv-{ds}",
                date=ds,
                time=None,
                type="dividend",
                title=f"{sym} Ex-Dividend",
                description="Source: yfinance",
                impact="low",
                related_symbols=[sym],
                is_watchlist_related=True,
            )
        )

    return events


async def _build_yfinance_events(
    symbols: List[str], date_from: date, date_to: date
) -> List[CalendarEventSchema]:
    """
    Async wrapper — fetches each symbol concurrently via run_in_executor
    so the FastAPI event loop is never blocked.
    """
    if not symbols:
        return []

    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _fetch_single_symbol_events, sym, date_from, date_to)
        for sym in symbols
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    events: List[CalendarEventSchema] = []
    for result in results:
        if isinstance(result, list):
            events.extend(result)
        # silently swallow exceptions from individual symbols

    return events


# ==================== P2-C: akshare A-Share ====================

def _is_a_share(code: str) -> bool:
    return code.isdigit() and len(code) == 6


def _fetch_akshare_dividends(
    a_share_codes: List[str], date_from: date, date_to: date
) -> List[CalendarEventSchema]:
    """Fetch A-share ex-dividend dates. Runs in a thread."""
    if not a_share_codes:
        return []
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return []

    events: List[CalendarEventSchema] = []
    for code in a_share_codes:
        try:
            df = ak.stock_zh_a_ex_right_date_sina(symbol=code)
            if df is None:
                continue
            import pandas as _pd
            if isinstance(df, _pd.DataFrame) and df.empty:
                continue
            date_col = next(
                (c for c in df.columns if "date" in c.lower() or "日期" in c or "除权" in c.lower()),
                None,
            )
            if date_col is None:
                continue
            for raw_date in df[date_col]:
                ex_date = _as_date(raw_date)
                if ex_date and _date_in_window(ex_date, date_from, date_to):
                    ds = ex_date.strftime("%Y-%m-%d")
                    events.append(CalendarEventSchema(
                        id=f"ak-{code}-exdiv-{ds}",
                        date=ds,
                        time=None,
                        type="dividend",
                        title=f"{code} 除权除息日",
                        description="来源: akshare",
                        impact="low",
                        related_symbols=[code],
                        is_watchlist_related=True,
                    ))
        except Exception:
            continue
    return events


def _fetch_akshare_ipos(date_from: date, date_to: date) -> List[CalendarEventSchema]:
    """Fetch upcoming A-share IPO dates. Runs in a thread."""
    try:
        import akshare as ak  # type: ignore
    except Exception:
        return []

    events: List[CalendarEventSchema] = []
    try:
        df = ak.stock_zh_a_new_financial_analysis_sina()
        if df is None:
            return []
        sub_col = next((c for c in df.columns if "申购" in c or "ipo" in c.lower() or "date" in c.lower()), None)
        name_col = next((c for c in df.columns if "名称" in c or "name" in c.lower()), None)
        code_col = next((c for c in df.columns if "代码" in c or "code" in c.lower()), None)
        if sub_col is None:
            return []
        for _, row in df.iterrows():
            sub_date = _as_date(row.get(sub_col))
            if sub_date and _date_in_window(sub_date, date_from, date_to):
                name = str(row.get(name_col, "新股")) if name_col else "新股"
                code = str(row.get(code_col, "")) if code_col else ""
                ds = sub_date.strftime("%Y-%m-%d")
                events.append(CalendarEventSchema(
                    id=f"ak-ipo-{code or name}-{ds}",
                    date=ds,
                    time=None,
                    type="ipo",
                    title=f"新股申购 · {name}",
                    description=f"A股新股 {code}",
                    impact="medium",
                    related_symbols=[code] if code else [],
                    is_watchlist_related=False,
                ))
    except Exception:
        pass
    return events


async def _build_akshare_events(
    watchlist_codes: List[str], date_from: date, date_to: date
) -> List[CalendarEventSchema]:
    """Async wrapper — fetch dividend + IPO concurrently."""
    a_share_codes = [c for c in watchlist_codes if _is_a_share(c)]
    loop = asyncio.get_event_loop()
    results = await asyncio.gather(
        loop.run_in_executor(None, _fetch_akshare_dividends, a_share_codes, date_from, date_to),
        loop.run_in_executor(None, _fetch_akshare_ipos, date_from, date_to),
        return_exceptions=True,
    )
    events: List[CalendarEventSchema] = []
    for r in results:
        if isinstance(r, list):
            events.extend(r)
    return events


# ==================== Endpoints ====================

@router.get("/events", response_model=CalendarResponse)
async def get_calendar_events(
    date_from: Optional[str] = Query(None, description="YYYY-MM-DD"),
    date_to: Optional[str]   = Query(None, description="YYYY-MM-DD"),
    watchlist_only: bool      = Query(False),
    types: Optional[str]      = Query(None, description="Comma-separated: earnings,dividend,ipo,economic,announcement"),
    current_user: User        = Depends(get_current_user),
    db: Session               = Depends(get_session),
):
    """
    Returns financial calendar events within [date_from, date_to].
    Data sources: yfinance (US stocks) + akshare (A-share dividends / IPOs).
    """
    today = date.today()
    try:
        from_dt = date.fromisoformat(date_from) if date_from else today
        to_dt   = date.fromisoformat(date_to)   if date_to   else today + timedelta(days=7)
    except ValueError:
        from_dt, to_dt = today, today + timedelta(days=7)

    watchlist_codes = _get_user_watchlist_codes(current_user, db)

    # Fetch all sources concurrently
    yf_events, ak_events = await asyncio.gather(
        _build_yfinance_events(watchlist_codes, from_dt, to_dt),
        _build_akshare_events(watchlist_codes, from_dt, to_dt),
    )
    events: List[CalendarEventSchema] = list(yf_events) + list(ak_events)

    # Deduplicate by (symbols, type, date)
    seen: set = set()
    deduped: List[CalendarEventSchema] = []
    for e in events:
        key = (tuple(sorted(e.related_symbols)), e.type, e.date)
        if key not in seen:
            seen.add(key)
            deduped.append(e)
    events = deduped

    # Filter by watchlist_only
    if watchlist_only:
        events = [e for e in events if e.is_watchlist_related]

    # Filter by types
    if types:
        type_set = {t.strip() for t in types.split(",")}
        events = [e for e in events if e.type in type_set]

    # Sort: date asc, timed events before all-day
    events.sort(key=lambda e: (e.date, e.time or "99:99"))

    return CalendarResponse(
        events=events,
        date_range={
            "from": from_dt.strftime("%Y-%m-%d"),
            "to":   to_dt.strftime("%Y-%m-%d"),
        }
    )
