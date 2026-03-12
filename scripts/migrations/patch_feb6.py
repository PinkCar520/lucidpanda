from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.fund_engine import FundEngine
from datetime import date

def patch_feb6_data():
    db = IntelligenceDB()
    engine = FundEngine(db=db)
    codes = db.get_watchlist_all_codes()

    print(f"🚀 正在补跑 2026-02-06 (周五) 的收盘估值数据...")
    
    # 获取当前行情（周六行情即为周五收盘价）
    valuations = engine.calculate_batch_valuation(codes)
    
    # 强制指定日期为 2026-02-06
    target_date = date(2026, 2, 6)
    count = 0
    
    for val in valuations:
        if 'error' in val: continue
        
        db.save_valuation_snapshot(
            trade_date=target_date,
            fund_code=val['fund_code'],
            est_growth=val['estimated_growth'],
            components_json=val['components'],
            sector_json=val.get('sector_attribution')
        )
        count += 1
        
    print(f"✅ 补跑成功！已为 {count} 只基金存入 2026-02-06 的复盘数据。")

if __name__ == "__main__":
    patch_feb6_data()
