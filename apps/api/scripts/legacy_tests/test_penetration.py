
import os
import re

import akshare as ak

# Disable proxies
os.environ['HTTP_PROXY'] = ''
os.environ['HTTPS_PROXY'] = ''
os.environ['ALL_PROXY'] = ''
os.environ['NO_PROXY'] = '*'

def extract_potential_master_name(feeder_name):
    # Remove suffix types like A/B/C/D
    name = re.sub(r'[A-Za-z]+$', '', feeder_name)
    # Remove "联接"
    name = name.replace('联接', '')
    # Remove "发起" (Initiated) or "发起式"
    name = name.replace('发起式', '').replace('发起', '')
    # Remove brackets
    name = re.sub(r'\(.*?\)', '', name)
    return name.strip()

def find_master_etf():
    # Test cases
    feeders = [
        {"code": "023765", "name": "华夏中证5G通信主题ETF联接C"},
        {"code": "021534", "name": "华夏有色金属ETF联接D"},
        {"code": "020274", "name": "富国中证细分化工产业主题ETF联接A"} # Assuming full name structure
    ]

    # We need to search.
    # Use ak.fund_name_em() to get the big list of all funds/ETFs?
    print("📋 Downloading full fund list to simulate search...")
    try:
        all_funds = ak.fund_name_em()
        print(f"Loaded {len(all_funds)} funds.")
    except Exception as e:
        print(f"Failed to load fund list: {e}")
        return

    # Check columns
    # Usually: 基金代码, 基金简称
    # Map code/name cols
    code_col = [c for c in all_funds.columns if '代码' in c][0]
    name_col = [c for c in all_funds.columns if '简称' in c][0]

    for f in feeders:
        print(f"\n🔍 Processing Feeder: {f['name']} ({f['code']})")
        target_name = extract_potential_master_name(f['name'])
        print(f"   Target Name key: '{target_name}'")

        # Search exact match or contains
        # Rules:
        # 1. Must contain target_name
        # 2. Must be an ETF (Code start with 51, 15, 56, 58?)
        # 3. Ideally name is shorter or equal (Master is clean)

        mask = all_funds[name_col].str.contains(target_name, regex=False)
        candidates = all_funds[mask]

        found = None
        for _, row in candidates.iterrows():
            c_code = str(row[code_col])
            c_name = str(row[name_col])

            # Simple ETF filter for China market
            # SH ETFs: 51xxxx, 56xxxx, 58xxxx
            # SZ ETFs: 15xxxx
            if c_code.startswith(('51', '15', '56', '58')):
                print(f"   ✅ Candidate ETF Found: {c_name} ({c_code})")
                found = c_code
                break # Take first likely one

        if not found:
            print("   ❌ No ETF parent found.")

if __name__ == "__main__":
    find_master_etf()
