#!/usr/bin/env python3
"""
Sync fund companies from akshare to fund_companies table,
then link fund_metadata.company_id using multi-pass fuzzy matching.

Achieves ~97% fill rate via:
  Pass 1: Short name prefix match (extracted from full company name)
  Pass 2: Short name contains match (for brand-prefixed fund names)
  Pass 3: Special rules for companies with brand ≠ short name
  Pass 4: Manual brand alias rules (e.g. 工银->工银瑞信, 大摩->摩根士丹利)
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import re
import hashlib
import akshare as ak
from src.lucidpanda.db.base import DBBase


def extract_short_name(full_name: str) -> str:
    """Extract brand short name from full company name."""
    suffixes = [
        '基金管理有限责任公司', '基金管理有限公司', '基金管理股份有限公司',
        '资产管理有限公司', '资产管理有限责任公司',
        '证券资产管理有限公司', '证券资产管理(广东)有限公司',
        '证券有限责任公司', '证券股份有限公司',
        '有限责任公司', '有限公司', '股份有限公司',
    ]
    name = re.sub(r'^(上海|北京|深圳|广州|成都|重庆|杭州|天津|南京)', '', full_name)
    for suf in suffixes:
        name = name.replace(suf, '')
    return name.strip()


# Brand aliases: fund name prefix -> keyword in fund_companies.name
# Used when the brand short name differs from what extract_short_name produces.
BRAND_ALIASES = {
    '工银':  '工银瑞信',
    '交银':  '交银施罗德',
    '摩根':  '摩根基金管理(中国)',
    '农银':  '农银汇理',
    '中邮':  '中邮创业',
    '华泰':  '华泰柏瑞',
    '光大':  '光大保德信',
    '人保':  '中国人保资产',
    '前海':  '前海开源',
    '大摩':  '摩根士丹利',
    '兴全':  '兴证全球',
    '中泰':  '中泰证券(上海)',
    '东证融汇': '东证融汇证券',
    '上海证券': '上海证券有限',
}


def sync_fund_companies():
    print("📥 Fetching fund companies from akshare...")
    try:
        df = ak.fund_aum_em()
        print(f"✅ Got {len(df)} companies")
    except Exception as e:
        print(f"❌ Failed to fetch: {e}")
        return False

    companies = []
    for _, row in df.iterrows():
        name = row['基金公司']
        company_id = int(hashlib.md5(name.encode('utf-8')).hexdigest()[:8], 16) % 1000000000
        companies.append({'company_id': company_id, 'name': name})

    db = DBBase()
    conn = db._get_conn()
    cur = conn.cursor()

    try:
        # ── Step 1: Populate fund_companies ──────────────────────────────
        # Clear FK references first, then clear companies
        cur.execute("UPDATE fund_metadata SET company_id = NULL")
        cur.execute("DELETE FROM fund_companies")
        for c in companies:
            cur.execute(
                "INSERT INTO fund_companies (company_id, name, full_name, establishment_date)"
                " VALUES (%s, %s, %s, NULL)",
                (c['company_id'], c['name'], c['name'])
            )
        # ── Step 2: Reset already done above ─────────────────────────────
        conn.commit()
        print(f"✅ Inserted {len(companies)} companies")

        total_linked = 0

        # ── Pass 1: Short name prefix match ──────────────────────────────
        linked = 0
        for c in companies:
            short = extract_short_name(c['name'])
            if len(short) < 2:
                continue
            cur.execute(
                "UPDATE fund_metadata SET company_id = %s"
                " WHERE company_id IS NULL AND fund_name LIKE %s",
                (c['company_id'], f"{short}%")
            )
            linked += cur.rowcount
        conn.commit()
        total_linked += linked
        print(f"  Pass 1 (prefix):   +{linked}")

        # ── Pass 2: Short name contains match ────────────────────────────
        linked = 0
        for c in companies:
            short = extract_short_name(c['name'])
            if len(short) < 2:
                continue
            cur.execute(
                "UPDATE fund_metadata SET company_id = %s"
                " WHERE company_id IS NULL AND fund_name ILIKE %s",
                (c['company_id'], f"%{short}%")
            )
            linked += cur.rowcount
        conn.commit()
        total_linked += linked
        print(f"  Pass 2 (contains): +{linked}")

        # ── Pass 3 & 4: Brand alias rules ────────────────────────────────
        linked = 0
        for brand_prefix, company_kw in BRAND_ALIASES.items():
            cur.execute(
                "SELECT company_id FROM fund_companies WHERE name LIKE %s LIMIT 1",
                (f"%{company_kw}%",)
            )
            row = cur.fetchone()
            if not row:
                print(f"  ⚠️  No company found for alias [{brand_prefix}] -> {company_kw}")
                continue
            company_id = row[0]
            cur.execute(
                "UPDATE fund_metadata SET company_id = %s"
                " WHERE company_id IS NULL AND fund_name LIKE %s",
                (company_id, f"{brand_prefix}%")
            )
            n = cur.rowcount
            if n:
                linked += n
        conn.commit()
        total_linked += linked
        print(f"  Pass 3 (aliases):  +{linked}")

        # ── Final stats ──────────────────────────────────────────────────
        cur.execute("SELECT COUNT(*) FROM fund_metadata WHERE company_id IS NOT NULL")
        filled = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM fund_metadata")
        total = cur.fetchone()[0]
        print(f"\n📊 Fill rate: {filled}/{total} ({filled/total*100:.1f}%)")
        print(f"   Total linked: {total_linked}")

    except Exception as e:
        conn.rollback()
        import traceback
        print(f"❌ DB error: {e}")
        traceback.print_exc()
        return False
    finally:
        conn.close()

    return True


if __name__ == "__main__":
    sync_fund_companies()
