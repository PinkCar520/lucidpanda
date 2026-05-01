import akshare as ak
import pandas as pd

print("--- Testing AkShare Global Gold (Sina) ---")
try:
    # 国际黄金分时线 (通常对应伦敦金)
    df = ak.futures_global_sina(symbol="黄金", period="分时")
    print(f"Points: {len(df)}")
    if not df.empty:
        print(df.tail(3))
except Exception as e:
    print(f"Error: {e}")

print("\n--- Testing AkShare Global Gold 5m (Sina) ---")
try:
    df_5m = ak.futures_global_sina(symbol="黄金", period="5分钟")
    print(f"5m Points: {len(df_5m)}")
    if not df_5m.empty:
        print(df_5m.tail(3))
except Exception as e:
    print(f"Error: {e}")
