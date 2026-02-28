#!/usr/bin/env python3
"""
强制回填最近 N 天的回测数据
只回填有历史数据可匹配的记录（Sina 只提供约 7 天历史）
"""
import sys
sys.path.insert(0, '.')

from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.backtest import BacktestEngine
from datetime import datetime, timedelta
import pytz

# 配置：只回填最近 5 天的数据
DAYS_TO_REPLAY = 5

db = IntelligenceDB()
engine = BacktestEngine(db)

print('='*70)
print(f'AlphaSignal 强制回测数据回填 (最近{DAYS_TO_REPLAY}天)')
print('='*70)

conn = db._get_conn()
cursor = conn.cursor()

# 获取最近 N 天待回填的记录
cursor.execute(f'''
    SELECT id, timestamp FROM intelligence
    WHERE (price_1h IS NULL OR price_12h IS NULL OR price_24h IS NULL)
      AND timestamp > NOW() - INTERVAL '{DAYS_TO_REPLAY} days'
    ORDER BY timestamp ASC
''')
records = cursor.fetchall()
print(f'\n待回填记录数：{len(records)}')

if not records:
    print('没有需要回填的记录')
    conn.close()
    sys.exit(0)

# 获取历史数据（Sina 提供约 7 天 1 分钟数据）
print('获取黄金历史数据...')
hist = engine._fetch_precise_hist()
if hist.empty:
    print('❌ 无法获取历史数据')
    conn.close()
    sys.exit(1)

print(f'✅ 获取到 {len(hist)} 条历史数据')
print(f'   时间范围：{hist.index[0]} 到 {hist.index[-1]}')

# 回填窗口
windows = {
    'price_15m': timedelta(minutes=15),
    'price_1h': timedelta(hours=1),
    'price_4h': timedelta(hours=4),
    'price_12h': timedelta(hours=12),
    'price_24h': timedelta(hours=24)
}

# 逐条回填
success_count = 0
failed_count = 0
print('\n开始回填...')

for record_id, record_time in records:
    try:
        if record_time.tzinfo is None:
            record_time = pytz.utc.localize(record_time)
        
        outcomes = {}
        for col, delta in windows.items():
            target_time = record_time + delta
            idx = hist.index.searchsorted(target_time)
            
            if idx < len(hist):
                matched_time = hist.index[idx]
                # 容错：3 天内
                if (matched_time - target_time).total_seconds() <= 3 * 86400:
                    outcomes[col] = round(float(hist.iloc[idx]['Close']), 2)
        
        if outcomes:
            set_clause = ', '.join([f'{k} = %s' for k in outcomes.keys()])
            values = list(outcomes.values()) + [record_id]
            cursor.execute(f'UPDATE intelligence SET {set_clause} WHERE id = %s', values)
            success_count += 1
        else:
            failed_count += 1
    except Exception as e:
        failed_count += 1

conn.commit()
conn.close()

print(f'\n✅ 回填完成')
print(f'   成功：{success_count} 条')
print(f'   失败：{failed_count} 条 (历史数据范围外)')
print('='*70)
