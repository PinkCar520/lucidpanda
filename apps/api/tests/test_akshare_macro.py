import akshare as ak

try:
    df = ak.news_economic_baidu(date="20260311")
    print("Columns:", df.columns.tolist())
    print("Head:\n", df.head(5).to_dict(orient="records"))
except Exception as e:
    print(f"Baidu error: {e}")

try:
    df = ak.macro_fx_indicator(symbol="美国", indicator="美国核心CPI年率")
    print("FX columns:", df.columns.tolist())
    print("FX Head:\n", df.head(1).to_dict(orient="records"))
except Exception as e:
    print(f"FX error: {e}")
