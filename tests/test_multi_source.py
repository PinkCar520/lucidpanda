import akshare as ak
import pandas as pd

def test_sources(code):
    print(f"--- Testing {code} ---")
    
    # Source 1: EastMoney (Current)
    try:
        df_em = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
        print(f"EM Status: {'OK' if not df_em.empty else 'Empty'}")
    except Exception as e:
        print(f"EM Error: {e}")

    # Source 2: Snowball (Xueqiu)
    try:
        # Note: 雪球接口有时需要特定的 header 或 token
        # 这里测试 akshare 封装的雪球或备选源
        df_xq = ak.fund_individual_basic_info_xq(symbol=code)
        print(f"Snowball Status: {'OK' if not df_xq.empty else 'Empty'}")
    except Exception as e:
        print(f"Snowball Error: {e}")

if __name__ == "__main__":
    test_sources('001618')
