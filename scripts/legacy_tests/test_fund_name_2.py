
import akshare as ak
import datetime

def check_cols(code):
    try:
        current_year = str(datetime.datetime.now().year - 1)
        df = ak.fund_portfolio_hold_em(symbol=code, date=current_year)
        if not df.empty:
            print(df.columns)
            print(df.iloc[0])
    except Exception as e:
        print(e)

if __name__ == "__main__":
    check_cols("022365")
