
import akshare as ak
import sys

def get_name(code):
    try:
        # Try individual basic info
        df = ak.fund_individual_basic_info_em(symbol=code)
        print(f"DEBUG: {df}")
        # Usually checking columns or rows
        # It's usually a wide table or a property table
    except Exception as e:
        print(e)

if __name__ == "__main__":
    get_name("022365")
