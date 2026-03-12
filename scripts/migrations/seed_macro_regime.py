#!/usr/bin/env python3
import sys
import os
from datetime import datetime
import pytz

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

def seed_fed_regimes():
    db = IntelligenceDB()
    
    # Simple Fed Regimes
    # 1: Dovish (Rate Cuts/Ease), -1: Hawkish (Rate Hikes/Tight), 0: Neutral
    regimes = [
        ("2021-01-01", 0, "Neutral / Post-COVID Accommodation"),
        ("2022-03-16", -1, "Hawkish / Fed starts aggressive hike cycle"),
        ("2024-09-18", 1, "Dovish / Fed starts rate cut cycle (50bps pivot)"),
    ]
    
    for date_str, value, desc in regimes:
        dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=pytz.UTC)
        db.save_indicator(dt, "FED_REGIME", value, percentile=None, description=desc)
        logger.info(f"✅ Seeded FED_REGIME: {date_str} -> {value} ({desc})")

if __name__ == "__main__":
    seed_fed_regimes()
