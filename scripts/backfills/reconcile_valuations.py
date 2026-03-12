#!/usr/bin/env python3
import sys
import os
import argparse
from datetime import datetime

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.alphasignal.core.fund_engine import FundEngine
from src.alphasignal.core.logger import logger

def main():
    parser = argparse.ArgumentParser(description="AlphaFunds Valuation Reconciliation Engine")
    parser.add_argument("--mode", choices=["snapshot", "reconcile"], required=True, 
                        help="snapshot: Freeze current valuations at 15:00; reconcile: Match with official NAVs")
    parser.add_argument("--date", help="Date for reconciliation (YYYY-MM-DD), defaults to yesterday")
    
    args = parser.parse_args()
    engine = FundEngine()
    
    if args.mode == "snapshot":
        logger.info("🚀 Triggering 15:00 Valuation Snapshot Task...")
        engine.take_all_funds_snapshot()
    
    elif args.mode == "reconcile":
        target_date = None
        if args.date:
            try:
                target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
            except ValueError:
                logger.error("❌ Invalid date format. Use YYYY-MM-DD")
                return
        
        logger.info(f"⚖️ Triggering Official Reconciliation Task for {target_date or 'yesterday'}...")
        engine.reconcile_official_valuations(target_date)

if __name__ == "__main__":
    main()
