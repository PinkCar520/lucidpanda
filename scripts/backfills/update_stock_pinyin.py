import os
from sqlalchemy import create_engine, text
from pypinyin import pinyin, Style

def get_pinyin_shorthand(name):
    if not name: return ""
    letters = pinyin(name, style=Style.FIRST_LETTER)
    return "".join([item[0].upper() for item in letters if item[0].isalnum()])

def update_pinyin():
    db_user = os.getenv("POSTGRES_USER", "alphasignal")
    db_pass = os.getenv("POSTGRES_PASSWORD", "secure_password")
    db_host = os.getenv("POSTGRES_HOST", "db")
    db_name = os.getenv("POSTGRES_DB", "alphasignal_core")
    
    url = f"postgresql://{db_user}:{db_pass}@{db_host}:5432/{db_name}"
    print(f"Connecting to database: {url}")
    engine = create_engine(url)
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT stock_code, stock_name FROM stock_metadata LIMIT 5"))
        stocks = result.fetchall()
        print("Here are 5 stocks and their pinyin shorthands to test:")
        for stock in stocks:
            code_str = str(stock[0])
            name = str(stock[1])
            shorthand = get_pinyin_shorthand(name)
            print(f"- Name: {name}, Code: {code_str}, Pinyin: {shorthand}")

if __name__ == "__main__":
    update_pinyin()
