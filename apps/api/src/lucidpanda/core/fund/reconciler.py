import json
import logging
import random
import re
import os
import time
from datetime import datetime, timedelta, date, timezone
from typing import Any

import akshare as ak
import pandas as pd
import requests

from src.lucidpanda.core.fund.valuation import calculate_batch_valuation
from src.lucidpanda.utils.market_calendar import (
    is_market_open,
    was_market_open_last_night,
)

logger = logging.getLogger(__name__)


def take_all_funds_snapshot(db: Any, redis_client: Any) -> int:
    """Batch take snapshots for all funds in various users' watchlists."""
    if not is_market_open('CN'):
        logger.info("⛱️ A-share market is closed today. Skipping all snapshots.")
        return 0

    codes = db.get_watchlist_all_codes()
    if not codes:
        return 0

    db_meta = db.get_fund_metadata_batch(codes)
    valuations = calculate_batch_valuation(db, redis_client, codes)

    trade_date = date.today()
    count = 0
    for val in valuations:
        if 'error' in val: continue
        f_code = val['fund_code']
        meta = db_meta.get(f_code, {})
        
        # QDII Gatekeeping
        if "QDII" in str(meta.get('type', '')) or "QDII" in str(meta.get('name', '')):
            region = 'US'
            name = meta.get('name', '')
            if any(k in name for k in ["恒生", "港", "HK", "H股"]): region = 'HK'
            elif any(k in name for k in ["日", "东京", "东证"]): region = 'JP'
            if not was_market_open_last_night(region): continue

        db.save_valuation_snapshot(
            trade_date=trade_date,
            fund_code=f_code,
            est_growth=val['estimated_growth'],
            components_json=val.get('components'),
            sector_json=val.get('sector_attribution')
        )
        count += 1
    return count


def ensure_archive_placeholders_exist(db: Any, days_lookback: int = 7) -> list[date]:
    """Check for missed trading days and create placeholder records."""
    today = date.today()
    codes = db.get_watchlist_all_codes()
    if not codes: return []

    backfilled_dates = []
    for i in range(1, days_lookback + 1):
        check_date = today - timedelta(days=i)
        if not is_market_open('CN', check_date): continue
        
        conn = db.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1 FROM fund_valuation_archive WHERE trade_date = %s LIMIT 1", (check_date,))
                if not cursor.fetchone():
                    for code in codes:
                        db.save_valuation_snapshot(trade_date=check_date, fund_code=code, est_growth=None)
                    backfilled_dates.append(check_date)
        finally:
            conn.close()
    return backfilled_dates


def reconcile_official_valuations(db: Any, target_date: Any = None, fund_codes: list[str] | None = None) -> int:
    """Fetch real growth for specific funds in the archive."""
    if not target_date:
        ensure_archive_placeholders_exist(db, days_lookback=14)

    conn = db.get_connection()
    pending_tasks = []
    try:
        from psycopg.rows import tuple_row
        with conn.cursor(row_factory=tuple_row) as cursor:
            sql_where = "WHERE official_growth IS NULL "
            params = []
            if target_date:
                sql_where += "AND trade_date = %s "; params.append(target_date)
            else:
                sql_where += "AND trade_date >= '2026-03-01' "
            if fund_codes:
                sql_where += "AND fund_code = ANY(%s) "; params.append(fund_codes)
            
            cursor.execute(f"SELECT trade_date, fund_code FROM fund_valuation_archive {sql_where} LIMIT 500", tuple(params))
            pending_tasks = cursor.fetchall()
    finally:
        conn.close()

    if not pending_tasks: return 0

    tasks_by_date = {}
    for d, c in pending_tasks:
        if isinstance(d, str): d = datetime.strptime(d, "%Y-%m-%d").date()
        if d not in tasks_by_date: tasks_by_date[d] = []
        tasks_by_date[d].append(c)

    total_updated = 0
    for t_date, codes in tasks_by_date.items():
        total_updated += _reconcile_date(db, t_date, codes)
    return total_updated


def _reconcile_date(db, trade_date, codes):
    """Internal multi-stage reconciliation for a specific date."""
    batch_results = {}
    is_recent = (date.today() - trade_date).days <= 3

    # Stage 1: Stealth Batch (EastMoney API)
    if is_recent:
        try:
            url = f"http://fund.eastmoney.com/Data/Fund_JJJZ_Data.aspx?t=1&page=1,20000&dt={int(time.time()*1000)}"
            headers = {"Referer": "http://fund.eastmoney.com/fund.html"}
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                dt_match = re.search(r'showDate\s*:\s*"(.*?)"', resp.text)
                if dt_match and dt_match.group(1) == trade_date.strftime('%Y-%m-%d'):
                    rows = re.findall(r'\["(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)",', resp.text)
                    for r in rows:
                        if r[0] in codes:
                            try: batch_results[r[0]] = float(r[7])
                            except Exception: continue
        except Exception as e:
            logger.warning(f"Stealth batch failed: {e}")

    # Stage 2: Individual Fetch with Proxy Disable
    count = 0
    orig_http = os.environ.get('HTTP_PROXY')
    orig_https = os.environ.get('HTTPS_PROXY')
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''

    try:
        for code in codes:
            if code in batch_results:
                db.update_official_nav(trade_date, code, batch_results[code])
                count += 1
                continue

            # Slow individual fetch
            try:
                time.sleep(random.uniform(0.5, 1.2))
                df = ak.fund_open_fund_info_em(symbol=code, indicator="单位净值走势")
                if not df.empty:
                    df['净值日期'] = pd.to_datetime(df['净值日期']).dt.date
                    match = df[df['净值日期'] == trade_date]
                    if not match.empty:
                        db.update_official_nav(trade_date, code, float(match.iloc[0]['日增长率']))
                        count += 1
            except Exception:
                # Backup Mobile API
                try:
                    b_url = f"https://fundmobapi.eastmoney.com/FundMApi/FundVarietieBackStageData.ashx?FCODE={code}&deviceid=Lucid&plat=Android"
                    b_json = requests.get(b_url, timeout=10).json()
                    if b_json.get('Datas') and b_json['Datas'].get('FSRQ') == trade_date.strftime('%Y-%m-%d'):
                        db.update_official_nav(trade_date, code, float(b_json['Datas'].get('JZL', 0)))
                        count += 1
                except Exception:
                    pass
    finally:
        if orig_http: os.environ['HTTP_PROXY'] = orig_http
        if orig_https: os.environ['HTTPS_PROXY'] = orig_https

    return count
