
import akshare as ak
import pandas as pd
import os

# Disable proxies
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''
os.environ['NO_PROXY'] = '*'

def check_feeder_holdings():
    # 023765: 华夏中证5G通信主题ETF联接C
    fund_code = "023765"
    print(f"🕵️‍♂️ Checking Holdings for Feeder Fund {fund_code}...")
    
    try:
        # 1. Standard Stock Holdings
        df_stock = ak.fund_portfolio_hold_em(symbol=fund_code, date="2025")
        print("\n--- Stock Holdings (Top rows) ---")
        if not df_stock.empty:
            print(df_stock[['季度', '股票代码', '股票名称', '占净值比例']].head(5))
        else:
            print("No stock holdings found.")
            
    except Exception as e:
        print(f"Stock Fetch Error: {e}")

    # Check if there's a specialized function for "Fund Holdings" (i.e. funds held by this fund)
    # Akshare documentation or common knowledge implies specific endpoints for FoF, 
    # but often standard portfolio API might filter.
    # Let's try to assume it might be treating ETFs as stocks or we need to find another endpoint.
    
    # Actually, for standard funds, AkShare might not separate ETF holdings well in the stock interface.
    # Let's see if the 'stock' list actually contains the ETF with specific code.
    
if __name__ == "__main__":
    check_feeder_holdings()
