#!/usr/bin/env python3
"""
One-time migration script (Enhanced):
1. Add BOTH pinyin_full AND pinyin_shorthand columns to fund_metadata and stock_metadata
2. Backfill both fields for all records using pypinyin
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from pypinyin import Style, pinyin
from src.lucidpanda.db.base import DBBase


def to_pinyin_full(name:
    str) -> str:
    if not name:
        return ''
    return ''.join([item[0].lower() for item in pinyin(name, style=Style.NORMAL)])

def to_pinyin_shorthand(name:
    str) -> str:
    if not name:
        return ''
    letters = pinyin(name, style=Style.FIRST_LETTER)
    return ''.join([item[0].upper() for item in letters if item[0].isalnum()])

def main():
    db = DBBase()
    conn = db._get_conn()
    cur = conn.cursor()

    # Step 1: Add columns
    print('🔧 Creating columns and indexes...')
    cur.execute('ALTER TABLE fund_metadata ADD COLUMN IF NOT EXISTS pinyin_full TEXT')
    cur.execute('ALTER TABLE fund_metadata ADD COLUMN IF NOT EXISTS pinyin_shorthand VARCHAR(50)')

    cur.execute('ALTER TABLE stock_metadata ADD COLUMN IF NOT EXISTS pinyin_full TEXT')
    cur.execute('ALTER TABLE stock_metadata ADD COLUMN IF NOT EXISTS pinyin_shorthand VARCHAR(50)')

    cur.execute('CREATE INDEX IF NOT EXISTS idx_fund_metadata_pinyin_full ON fund_metadata (pinyin_full)')
    cur.execute('CREATE INDEX IF NOT EXISTS idx_stock_metadata_pinyin_full ON stock_metadata (pinyin_full)')
    conn.commit()
    print('✅ Columns and indexes ready')

    # Step 2: Backfill fund_metadata
    cur.execute('SELECT fund_code, fund_name FROM fund_metadata WHERE pinyin_full IS NULL OR pinyin_shorthand IS NULL')
    rows = cur.fetchall()
    print(f'📝 Backfilling {len(rows)} funds...')
    for i, (code, name) in enumerate(rows):
        cur.execute('UPDATE fund_metadata SET pinyin_full = %s, pinyin_shorthand = %s WHERE fund_code = %s',
                    (to_pinyin_full(name), to_pinyin_shorthand(name), code))
        if i % 1000 == 0 and i > 0:
            conn.commit()
            print(f'   {i}/{len(rows)}')
    conn.commit()
    print('✅ fund_metadata done')

    # Step 3: Backfill stock_metadata
    cur.execute('SELECT stock_code, stock_name FROM stock_metadata WHERE pinyin_full IS NULL OR pinyin_shorthand IS NULL')
    rows = cur.fetchall()
    print(f'📝 Backfilling {len(rows)} stocks...')
    for code, name in rows:
        cur.execute('UPDATE stock_metadata SET pinyin_full = %s, pinyin_shorthand = %s WHERE stock_code = %s',
                    (to_pinyin_full(name), to_pinyin_shorthand(name), code))
    conn.commit()
    print('✅ stock_metadata done')

    conn.close()
    print('\n🎉 All done! API search should now work completely.')


if __name__ == '__main__':
    main()
