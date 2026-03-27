#!/usr/bin/env python3
"""
清理并重新回填回测数据

修复了黄金价格数据源后，需要：
1. 清空之前错误的回测数据 (price_1h, price_12h, price_24h 等)
2. 使用新的正确数据源重新回填
"""

import sys

sys.path.insert(0, '.')

from src.lucidpanda.core.backtest import BacktestEngine
from src.lucidpanda.core.database import IntelligenceDB

db = IntelligenceDB()
engine = BacktestEngine(db)

print('='*70)
print('LucidPanda 回测数据清理与重新回填')
print('='*70)

# 步骤 1: 统计需要清理的数据
print()
print('【步骤 1】统计现有回测数据')
print('-'*70)

conn = db._get_conn()
cursor = conn.cursor()

cursor.execute('''
    SELECT COUNT(*) 
    FROM intelligence 
    WHERE price_1h IS NOT NULL 
       OR price_12h IS NOT NULL 
       OR price_24h IS NOT NULL
''')
count_with_outcome = cursor.fetchone()[0]
print(f'已有回测结果的记录数：{count_with_outcome}')

# 检查异常数据 (触发价>3000 但结果价<3000)
cursor.execute('''
    SELECT COUNT(*) 
    FROM intelligence 
    WHERE gold_price_snapshot > 3000 
      AND price_1h IS NOT NULL 
      AND price_1h < 3000
''')
abnormal_count = cursor.fetchone()[0]
print(f'异常数据条数 (单位不一致): {abnormal_count}')

conn.close()

# 步骤 2: 清空错误的回测数据
print()
print('【步骤 2】清空回测数据 (price_15m, price_1h, price_4h, price_12h, price_24h)')
print('-'*70)

confirm = input('是否确认清空所有回测数据？(输入 yes 确认): ')
if confirm != 'yes':
    print('❌ 操作已取消')
    sys.exit(0)

conn = db._get_conn()
cursor = conn.cursor()

cursor.execute('''
    UPDATE intelligence 
    SET price_15m = NULL, 
        price_1h = NULL, 
        price_4h = NULL, 
        price_12h = NULL, 
        price_24h = NULL
    WHERE price_1h IS NOT NULL 
       OR price_12h IS NOT NULL 
       OR price_24h IS NOT NULL
''')

updated = cursor.rowcount
conn.commit()
conn.close()

print(f'✅ 已清空 {updated} 条记录的回测数据')

# 步骤 3: 重新回填
print()
print('【步骤 3】重新执行回测回填')
print('-'*70)

# 重置引擎状态
engine.last_sync_attempt = engine.last_sync_attempt.replace(year=2000)  # 强制允许同步
engine.sync_outcomes()

print()
print('='*70)
print('完成!')
print('='*70)
