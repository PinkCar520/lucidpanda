import os
import sys
import logging
from datetime import datetime, date, timedelta
import akshare as ak
import pandas as pd
from sqlmodel import Session, select
import math

# Ensure src is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.lucidpanda.core.logger import logger
from src.lucidpanda.infra.database.connection import engine
from src.lucidpanda.models.macro_event import MacroEvent

def _clean_str(val):
    if isinstance(val, float) and math.isnan(val):
        return None
    res = str(val).strip()
    return None if res in ["nan", "None", "", "-"] else res

def sync_macro_calendar(days_ahead: int = 14):
    logger.info(f"Starting Macro Calendar Sync: scanning {days_ahead} days ahead.")
    
    today = datetime.now().date()
    # Use news_economic_baidu for each day in the window
    dfs = []
    for i in range(days_ahead + 1):
        target_date = today + timedelta(days=i)
        d_str = target_date.strftime("%Y%m%d")
        try:
            day_df = ak.news_economic_baidu(date=d_str)
            if day_df is not None and not day_df.empty:
                dfs.append(day_df)
        except Exception as e:
            logger.warning(f"Failed to fetch macro data for {d_str}: {e}")
            
    if not dfs:
        logger.warning("No macro data returned from akshare.")
        return
        
    df = pd.concat(dfs, ignore_index=True)
        
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
                
                # Check for nan/float parsing issues
                if isinstance(importance, float) and math.isnan(importance):
                    importance = 1
                elif isinstance(importance, str):
                    import re
                    # extract digits from string like '3星'
                    m = re.search(r'\d+', importance)
                    importance = int(m.group()) if m else 1
                else:
                    try:
                        importance = int(importance)
                    except Exception:
                        importance = 1
                        
                if importance < 2:
                    continue
                    
                impact_level = "high" if importance >= 2 else "medium"
                
                # 3. Parse fields
                country = str(row.get("地区", "Global"))
                title = str(row.get("事件", ""))
                event_code = f"{country}_{title[:10]}" # Generate a pseudo unique code
                
                # --- NOISE REDUCTION FILTER ---
                # We KEEP Gold, Silver, and Crude Oil as they are critical to the fund's strategy.
                # We ONLY remove irrelevant agricultural and non-core industrial noise.
                noise_keywords = [
                    "农产品", "大豆", "玉米", "小麦", "棉花", "豆粕", "菜粕", "苹果",
                    "红枣", "玻璃", "纯碱", "铁矿石", "螺纹钢", "猪肉", "生猪"
                ]
                if any(kw in title for kw in noise_keywords):
                    continue
                # ------------------------------
                
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
