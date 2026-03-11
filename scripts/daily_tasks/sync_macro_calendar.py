import os
import sys
import logging
from datetime import datetime, date, timedelta
import akshare as ak
from sqlmodel import Session, select
import math

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.alphasignal.core.logger import logger
from src.alphasignal.infra.database.connection import engine
from src.alphasignal.models.macro_event import MacroEvent

def _clean_str(val):
    if isinstance(val, float) and math.isnan(val):
        return None
    res = str(val).strip()
    return None if res in ["nan", "None", "", "-"] else res

def sync_macro_calendar(days_ahead: int = 14):
    logger.info(f"Starting Macro Calendar Sync: scanning {days_ahead} days ahead.")
    
    today = datetime.now().date()
    # Typically ak.macro_cons_gold() returns a chunk of current and upcoming events
    try:
        df = ak.macro_cons_gold()
    except Exception as e:
        logger.error(f"Failed to fetch macro data: {e}")
        return
        
    if df is None or df.empty:
        logger.warning("No macro data returned from akshare.")
        return
        
    # Standardize columns: ['日期', '时间', '地区', '事件', '公布', '预期', '前值', '重要性']
    records_inserted = 0
    records_updated = 0
    
    with Session(engine) as session:
        for _, row in df.iterrows():
            try:
                # 1. Parse Date
                d_val = row.get("日期")
                if isinstance(d_val, date):
                    event_date = d_val
                elif isinstance(d_val, str):
                    # string like '2026-03-11'
                    event_date = datetime.strptime(d_val[:10], "%Y-%m-%d").date()
                else:
                    continue
                    
                # We only want to keep data for a valid window
                if not (today - timedelta(days=7)) <= event_date <= (today + timedelta(days=days_ahead)):
                    continue
                    
                # 2. Filter out low impact noise (keep >= 3 stars)
                importance = row.get("重要性", 1)
                if isinstance(importance, str) and importance.isdigit():
                    importance = int(importance)
                if importance < 3:
                    continue
                    
                impact_level = "high" if importance >= 4 else "medium"
                
                # 3. Parse fields
                country = str(row.get("地区", "Global"))
                title = str(row.get("事件", ""))
                event_code = f"{country}_{title[:10]}" # Generate a pseudo unique code
                
                t_val = str(row.get("时间", ""))
                release_time = t_val if t_val and len(t_val) >= 4 and t_val != "nan" else None
                
                # 4. Upsert Logic (match by date and title to avoid duplicates)
                stmt = select(MacroEvent).where(
                    MacroEvent.release_date == event_date,
                    MacroEvent.title == title
                )
                existing = session.exec(stmt).first()
                
                if existing:
                    # Update dynamic values
                    existing.actual_value = _clean_str(row.get("公布"))
                    existing.forecast_value = _clean_str(row.get("预期"))
                    existing.previous_value = _clean_str(row.get("前值"))
                    existing.updated_at = datetime.utcnow()
                    session.add(existing)
                    records_updated += 1
                else:
                    # Insert new
                    new_event = MacroEvent(
                        event_code=event_code,
                        release_date=event_date,
                        release_time=release_time,
                        country=country,
                        title=title,
                        impact_level=impact_level,
                        actual_value=_clean_str(row.get("公布")),
                        forecast_value=_clean_str(row.get("预期")),
                        previous_value=_clean_str(row.get("前值")),
                        source="akshare_jin10"
                    )
                    session.add(new_event)
                    records_inserted += 1
                    
            except Exception as e:
                logger.warning(f"Error processing macro row {row}: {e}")
                
        session.commit()
    
    logger.info(f"Macro Sync Complete. Inserted: {records_inserted}, Updated: {records_updated}")

if __name__ == "__main__":
    sync_macro_calendar()
