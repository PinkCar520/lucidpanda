import json
import logging
from datetime import datetime, date, timedelta
import pandas as pd
from sqlmodel import Session, select
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from src.alphasignal.infra.database.connection import engine
from src.alphasignal.models.macro_event import MacroEvent
from src.alphasignal.core.logger import logger

def sync_market_holidays():
    """Sync market holidays for US, CN, HK (using known 2026/2027 static holidays or APIs)"""
    logger.info("Starting Market Holiday Sync")
    
    # In a fully mature system, we would use pandas_market_calendars for NYSE, 
    # and akshare for SSE/SZSE. Since pandas_market_calendars might not be installed,
    # we can seed the most critical US/HK/CN holidays for the current year (2026) manually
    # or via available akshare APIs.
    
    # 2026 Key US Holidays (NYSE/NASDAQ closed)
    us_holidays_2026 = [
        ("2026-01-01", "元旦"),
        ("2026-01-19", "马丁·路德·金纪念日"),
        ("2026-02-16", "华盛顿诞辰纪念日(总统日)"),
        ("2026-04-03", "耶稣受难日"),
        ("2026-05-25", "阵亡将士纪念日"),
        ("2026-06-19", "六月节"),
        ("2026-07-03", "独立日(提前休市/休假)"),
        ("2026-09-07", "劳工节"),
        ("2026-11-26", "感恩节"),
        ("2026-12-25", "圣诞节")
    ]
    
    # 2026 Key CN Holidays (A-Share closed) - Estimations based on standard lunar calendar
    cn_holidays_2026 = [
        ("2026-01-01", "元旦"),
        ("2026-02-16", "春节"),
        ("2026-02-17", "春节"),
        ("2026-02-18", "春节"),
        ("2026-04-06", "清明节"),
        ("2026-05-01", "劳动节"),
        ("2026-06-19", "端午节"),
        ("2026-09-25", "中秋节"), # Approximate lunar dates
        ("2026-10-01", "国庆节"),
        ("2026-10-02", "国庆节"),
        ("2026-10-05", "国庆节")
    ]
    
    # 2026 Key HK Holidays (HKEX closed)
    hk_holidays_2026 = [
        ("2026-01-01", "元旦"),
        ("2026-02-16", "农历年初一"),
        ("2026-02-17", "农历年初二"),
        ("2026-02-18", "农历年初三"),
        ("2026-04-03", "耶稣受难日"),
        ("2026-04-06", "清明节"),
        ("2026-04-07", "复活节星期一"),
        ("2026-05-01", "劳动节"),
        ("2026-05-24", "佛诞"),
        ("2026-06-19", "端午节"),
        ("2026-07-01", "香港特别行政区成立纪念日"),
        ("2026-09-26", "中秋节翌日"),
        ("2026-10-01", "国庆节"),
        ("2026-10-23", "重阳节"),
        ("2026-12-25", "圣诞节"),
        ("2026-12-26", "圣诞节后第一个周日")
    ]
    
    to_insert = []
    
    for dt_str, name in us_holidays_2026:
        to_insert.append({"date": dt_str, "name": f"美股休市 - {name}", "country": "US"})
        
    for dt_str, name in cn_holidays_2026:
        to_insert.append({"date": dt_str, "name": f"A股休市 - {name}", "country": "CN"})
        
    for dt_str, name in hk_holidays_2026:
        to_insert.append({"date": dt_str, "name": f"港股休市 - {name}", "country": "HK"})
        
    records_inserted = 0
    records_updated = 0
    
    with Session(engine) as session:
        for item in to_insert:
            event_date = datetime.strptime(item["date"], "%Y-%m-%d").date()
            title = item["name"]
            country = item["country"]
            
            stmt = select(MacroEvent).where(
                MacroEvent.release_date == event_date,
                MacroEvent.title == title
            )
            existing = session.exec(stmt).first()
            
            if existing:
                existing.updated_at = datetime.utcnow()
                session.add(existing)
                records_updated += 1
            else:
                new_event = MacroEvent(
                    event_code=f"HOLIDAY_{country}_{event_date.strftime('%Y%m%d')}",
                    release_date=event_date,
                    release_time="00:00",
                    country=country,
                    title=title,
                    impact_level="high", # Treated as high impact
                    actual_value="Closed",
                    forecast_value="Closed",
                    previous_value="",
                    source="system_holiday"
                )
                session.add(new_event)
                records_inserted += 1
                
        session.commit()
    
    logger.info(f"Holiday Sync Complete. Inserted: {records_inserted}, Updated: {records_updated}")

if __name__ == "__main__":
    sync_market_holidays()
