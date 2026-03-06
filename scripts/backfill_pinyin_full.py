#!/usr/bin/env python3
"""
One-time migration script:
1. Add pinyin_full column to fund_metadata and stock_metadata (IF NOT EXISTS)
2. Backfill pinyin_full for all records using pypinyin
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pypinyin import pinyin, Style
from src.alphasignal.db.base import DBBase


def to_pinyin_full(name: str) -> str:
    if not name:
        return ''
    return ''.join([item[0].lower() for item in pinyin(name, style=Style.NORMAL)])


def main():
    db = DBBase()
    conn = db._get_conn()
    cur = conn.cursor()

    # Step 1: Add columns
    cur.execute('ALTER TABLE fund_metadata ADD COLUMN IF NOT EXISTS pinyin_full TEXT')
    cur.execute('ALTER TABLE stock_metadata ADD COLUMN IF NOT EXISTS pinyin_full TEXT')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_fund_metadata_pinyin_full ON fund_metadata (pinyin_full)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_metadata_pinyin_full ON stock_metadata (pinyin_full)')
    conn.commit()
    print('✅ Columns and indexes ready')

    # Step 2: Backfill fund_metadata
    cur.execute('SELECT fund_code, fund_name FROM fund_metadata WHERE pinyin_full IS NULL')
    rows = cur.fetchall()
    print(f'📝 Backfilling {len(rows)} funds...')
    for i, (code, name) in enumerate(rows):
        cur.execute('UPDATE fund_metadata SET pinyin_full = %s WHERE fund_code = %s',
                    (to_pinyin_full(name), code))
        if i % 5000 == 0 and i > 0:
            conn.commit()
            print(f'   {i}/{len(rows)}')
    conn.commit()
    print(f'✅ fund_metadata done ({len(rows)} records)')

    # Step 3: Backfill stock_metadata
    cur.execute('SELECT stock_code, stock_name FROM stock_metadata WHERE pinyin_full IS NULL')
    rows = cur.fetchall()
    print(f'📝 Backfilling {len(rows)} stocks...')
    for code, name in rows:
        cur.execute('UPDATE stock_metadata SET pinyin_full = %s WHERE stock_code = %s',
                    (to_pinyin_full(name), code))
    conn.commit()
    print(f'✅ stock_metadata done ({len(rows)} records)')

    conn.close()
    print('\n🎉 All done.')


if __name__ == '__main__':
    main()
