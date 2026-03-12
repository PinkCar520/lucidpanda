
import akshare as ak
try:
    df = ak.fund_individual_basic_info_xq(symbol="022365")
    print(df)
except Exception as e:
    print(e)
