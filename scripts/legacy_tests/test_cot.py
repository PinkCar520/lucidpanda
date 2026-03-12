import requests
import zipfile
import io
import pandas as pd
from datetime import datetime

def test_fetch_cot():
    url = "https://www.cftc.gov/files/dea/history/com_disagg_txt_2025.zip"
    print(f"Downloading {url}...")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        z = zipfile.ZipFile(io.BytesIO(r.content))
        # Usually there is only one file inside
        filename = z.namelist()[0]
        print(f"Extracting {filename}...")
        with z.open(filename) as f:
            df = pd.read_csv(f, low_memory=False)
            
        print(f"Total rows: {len(df)}")
        # Filter for Gold
        gold_df = df[df['Market_and_Exchange_Names'].str.contains('GOLD', na=False, case=False)]
        
        if not gold_df.empty:
            print("Found Gold data!")
            print("Columns:", df.columns.tolist()[:30])
            # Common names: 'Report_Date_as_MM_DD_YYYY' or 'Report_Date_as_YYYY-MM-DD'
            # Let's see...
        else:
            print("Gold data NOT found in this file.")
            print("Available codes (first 20):", df['CFTC_Market_Code'].unique()[:20])
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_fetch_cot()
