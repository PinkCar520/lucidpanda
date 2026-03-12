import yfinance as yf
from datetime import datetime
import pandas as pd

def check_gold_data():
    print("Checking Gold Futures (GC=F) data for Jan 2026...")
    ticker = yf.Ticker("GC=F")
    
    # Fetch data
    start_date = "2026-01-01"
    end_date = "2026-01-31"
    
    try:
        df = ticker.history(start=start_date, end=end_date, interval="1h")
        
        if df.empty:
            print("❌ No data found for GC=F in this range.")
        else:
            print(f"✅ Data found! {len(df)} rows.")
            print("\nFirst 5 rows:")
            print(df.head()[['Open', 'High', 'Low', 'Close']])
            print("\nLast 5 rows:")
            print(df.tail()[['Open', 'High', 'Low', 'Close']])
            
    except Exception as e:
        print(f"❌ Error fetching data: {e}")

if __name__ == "__main__":
    check_gold_data()

