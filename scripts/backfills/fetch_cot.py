#!/usr/bin/env python3
import sys
import os
import requests
import zipfile
import io
import pandas as pd
from datetime import datetime
import pytz

# Add project path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

class COTFetcher:
    def __init__(self):
        self.db = IntelligenceDB()
        self.market_code = '088691' # Gold COMEX
        
    def fetch_year(self, year):
        url = f"https://www.cftc.gov/files/dea/history/com_disagg_txt_{year}.zip"
        logger.info(f"📥 Fetching COT data for {year}...")
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            z = zipfile.ZipFile(io.BytesIO(r.content))
            filename = z.namelist()[0]
            with z.open(filename) as f:
                df = pd.read_csv(f, low_memory=False)
            
            # Gold filter
            # Using code check is robust once verified
            # market_code might have spaces in some years, check carefully
            df['CFTC_Market_Code'] = df['CFTC_Market_Code'].astype(str).str.strip()
            gold_df = df[df['CFTC_Market_Code'] == '088691'].copy()
            
            if gold_df.empty:
                # Fallback to name search
                gold_df = df[df['Market_and_Exchange_Names'].str.contains('GOLD - COMMODITY EXCHANGE INC.', na=False, case=False)].copy()
            
            return gold_df
        except Exception as e:
            logger.error(f"❌ Failed to fetch COT {year}: {e}")
            return pd.DataFrame()

    def process_and_save(self, start_year=2023, end_year=2025):
        all_dfs = []
        for year in range(start_year, end_year + 1):
            df = self.fetch_year(year)
            if not df.empty:
                all_dfs.append(df)
        
        if not all_dfs:
            logger.error("❌ No COT data found for any year.")
            return
        
        combined_df = pd.concat(all_dfs)
        combined_df['Report_Date_as_YYYY-MM-DD'] = pd.to_datetime(combined_df['Report_Date_as_YYYY-MM-DD'])
        combined_df = combined_df.sort_values('Report_Date_as_YYYY-MM-DD')
        
        # Calculate Net Position
        combined_df['net_managed_money'] = combined_df['M_Money_Positions_Long_All'] - combined_df['M_Money_Positions_Short_All']
        
        # Calculate Percentile (3-year rolling or all time in this set)
        # Using Rank percentile
        combined_df['percentile'] = combined_df['net_managed_money'].rolling(window=52*3, min_periods=20).apply(
            lambda x: (x.rank(pct=True).iloc[-1] * 100) if not x.empty else 50
        )
        
        # Save to DB
        saved_count = 0
        for _, row in combined_df.iterrows():
            dt = row['Report_Date_as_YYYY-MM-DD'].replace(tzinfo=pytz.UTC)
            val = float(row['net_managed_money'])
            pct = float(row['percentile']) if not pd.isna(row['percentile']) else 50.0
            
            # Description
            longs = int(row['M_Money_Positions_Long_All'])
            shorts = int(row['M_Money_Positions_Short_All'])
            desc = f"Managed Money: {longs} Longs, {shorts} Shorts"
            
            self.db.save_indicator(dt, "COT_GOLD_NET", val, pct, desc)
            saved_count += 1
            
        logger.info(f"✅ Successfully processed and saved {saved_count} COT records.")

if __name__ == "__main__":
    fetcher = COTFetcher()
    # Fetch from 2021 to ensure percentile calculation has enough baseline
    fetcher.process_and_save(2021, 2025)
