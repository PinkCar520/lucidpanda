import json
import logging
import threading
from datetime import datetime
from typing import Any

import requests
from src.lucidpanda.core.fund.holdings import update_fund_holdings
from src.lucidpanda.core.fund.metadata import (
    get_confidence_level,
    get_fund_name,
    get_industry_map,
    identify_index_proxy,
    identify_shadow_etf,
    infer_risk_level,
)
from src.lucidpanda.core.fund.utils import (
    calculate_fee_drag_pct,
)
from src.lucidpanda.utils import format_iso8601

logger = logging.getLogger(__name__)


def calculate_realtime_valuation(db: Any, redis_client: Any, fund_code: str) -> dict[str, Any]:
    """Calculate live estimated NAV growth based on holdings."""
    # 0. Check Cache
    if redis_client:
        cached_val = redis_client.get(f"fund:valuation:{fund_code}")
        if cached_val:
            return json.loads(cached_val)

    # 1. Check/Identify Relationships
    fund_name = get_fund_name(db, redis_client, fund_code)
    fund_meta = db.get_fund_metadata_batch([fund_code]).get(fund_code, {})
    relationship = db.get_fund_relationship(fund_code)

    if not relationship:
        parent_code = identify_shadow_etf(db, fund_code, fund_name)
        if parent_code:
            relationship = {"parent_code": parent_code, "ratio": 0.95, "relation_type": "ETF_FEEDER"}

    if relationship:
        # Shadow/Proxy pricing logic
        return _calculate_shadow_valuation(db, redis_client, fund_code, fund_name, fund_meta, relationship)

    # 2. Check Index Proxy heuristic
    p_code, ratio = identify_index_proxy(db, fund_code, fund_name)
    if p_code:
        # Re-run with the new relationship
        return calculate_realtime_valuation(db, redis_client, fund_code)

    # 3. Standard Holdings Logic
    return _calculate_holdings_valuation(db, redis_client, fund_code, fund_name, fund_meta)


def _calculate_shadow_valuation(db, redis_client, fund_code, fund_name, fund_meta, relationship):
    parent_code = relationship['parent_code']
    rel_type = relationship.get('relation_type', 'ETF_FEEDER')
    ratio = relationship.get('ratio', 0.95)

    secid = _get_secid(parent_code)
    try:
        url = f"http://qt.gtimg.cn/q={secid}"
        res = requests.get(url, timeout=3)
        content = res.content.decode('gbk', errors='ignore')

        if '=' in content:
            val_part = content.split('=', 1)[1].strip('"')
            parts = val_part.split('~')
            if len(parts) > 32:
                price = float(parts[3])
                pct = float(parts[32])
                real_name = parts[1]
                est_growth = pct * ratio

                dynamic_bias = db.get_recent_bias(fund_code, days=7)
                if abs(dynamic_bias) > 0.001:
                    est_growth -= dynamic_bias

                # FX
                if "QDII" in fund_name:
                    currency = _infer_currency(fund_name)
                    fx_change = db.get_fx_rate_change(currency)
                    est_growth += fx_change * 0.9

                fee_drag, annual_fee, daily_fee, day_progress, _ = calculate_fee_drag_pct(
                    fund_code=fund_code, db=db, fund_meta=fund_meta, fund_name=fund_name
                )
                est_growth -= fee_drag

                result = {
                    "fund_code": fund_code,
                    "fund_name": fund_name,
                    "status": "active",
                    "estimated_growth": round(est_growth, 4),
                    "total_weight": ratio * 100,
                    "components": [{
                        "code": parent_code, "name": real_name, "price": price,
                        "change_pct": pct, "impact": est_growth, "weight": ratio * 100
                    }],
                    "sector_attribution": {},
                    "timestamp": format_iso8601(datetime.now()),
                    "source": f"{rel_type} ({parent_code})",
                    "fee_drag": {
                        "annual_fee_pct": round(annual_fee, 6),
                        "daily_fee_pct": round(daily_fee, 6),
                        "applied_drag_pct": round(fee_drag, 6),
                        "day_progress": round(day_progress, 6)
                    }
                }
                if redis_client:
                    redis_client.setex(f"fund:valuation:{fund_code}", 180, json.dumps(result))
                return result
    except Exception as e:
        logger.error(f"Shadow valuation failed for {fund_code}: {e}")
    return {"error": "Shadow valuation failed"}


def _calculate_holdings_valuation(db, redis_client, fund_code, fund_name, fund_meta):
    holdings = db.get_fund_holdings(fund_code)
    if not holdings:
        sync_key = f"syncing:holdings:{fund_code}"
        is_syncing = redis_client.get(sync_key) if redis_client else False
        if not is_syncing:
            if redis_client: redis_client.setex(sync_key, 300, "1")
            threading.Thread(target=update_fund_holdings, args=(db, fund_code,), daemon=True).start()
        return {"status": "syncing", "message": "Consulting holdings..."}

    # Market logic
    holding_codes = [h.get('stock_code') or h.get('code') for h in holdings]
    # (Simplified for export: in reality we'd batch fetch a/hk snapshots)
    # Re-use the existing logic or similar optimized path
    # For now, we'll keep the facade calls until all logic is moved
    return _batch_valuation_logic(db, redis_client, [fund_code])[0]


def calculate_batch_valuation(db: Any, redis_client: Any, fund_codes: list[str], summary: bool = False) -> list[dict[str, Any]]:
    """Batch valuation for multiple funds."""
    return _batch_valuation_logic(db, redis_client, fund_codes, summary)


def _batch_valuation_logic(db, redis_client, fund_codes, summary=False):
    # This is a large block extracted from fund_engine.py
    # Refactoring slightly to use the new modules
    fund_meta_map = {}
    fund_name_map = {}
    missing_meta_codes = []

    if redis_client:
        cached_meta = redis_client.mget([f"fund:meta:{c}" for c in fund_codes])
        for code, meta_json in zip(fund_codes, cached_meta, strict=False):
            if meta_json:
                try:
                    meta = json.loads(meta_json)
                    fund_meta_map[code] = meta
                    fund_name_map[code] = meta['name']
                except Exception:
                    missing_meta_codes.append(code)
            else:
                missing_meta_codes.append(code)
    else:
        missing_meta_codes = fund_codes

    if missing_meta_codes:
        db_meta = db.get_fund_metadata_batch(missing_meta_codes)
        for c, m in db_meta.items():
            fund_meta_map[c] = m
            fund_name_map[c] = m['name']
            if redis_client:
                redis_client.setex(f"fund:meta:{c}", 86400 * 7, json.dumps(m))

    all_holdings = {}
    stock_map = {}
    shadow_map = {}

    for f_code in fund_codes:
        rel = db.get_fund_relationship(f_code)
        if not rel:
            p_code = identify_shadow_etf(db, f_code, fund_name_map.get(f_code))
            if p_code: rel = {"parent_code": p_code, "ratio": 0.95, "relation_type": "ETF_FEEDER"}
            else:
                p_code, ratio = identify_index_proxy(db, f_code, fund_name_map.get(f_code))
                if p_code: rel = {"parent_code": p_code, "ratio": ratio, "relation_type": "INDEX_PROXY"}

        if rel:
            shadow_map[f_code] = rel
            stock_map[rel['parent_code']] = _get_secid(rel['parent_code'])
        else:
            holdings = db.get_fund_holdings(f_code)
            if not holdings:
                _trigger_holdings_sync(db, redis_client, f_code)
                all_holdings[f_code] = None
            else:
                all_holdings[f_code] = holdings
                for h in holdings:
                    s_code = h.get('stock_code') or h.get('code')
                    if s_code: stock_map[s_code] = _get_secid(s_code)

    # Fetch Quotes
    secids = list(set(stock_map.values()))
    quotes = _fetch_batch_quotes(secids)

    # Combine Results
    results = []
    industry_map = get_industry_map(db, redis_client, list(stock_map.keys())) if not summary else {}

    for f_code in fund_codes:
        res = _process_single_fund_batch(db, redis_client, f_code, shadow_map, all_holdings, quotes, industry_map, fund_meta_map, fund_name_map, summary)
        results.append(res)

    return results


def _get_secid(code: str) -> str:
    if code.startswith(('sh', 'sz', 'hk', 'us')): return code
    if code.isdigit():
        if len(code) == 6:
            if code.startswith(('6', '9')): return f"sh{code}"
            if code.startswith(('0', '3')): return f"sz{code}"
            if code.startswith(('8', '4')): return f"bj{code}"
            return f"sz{code}"
        if len(code) == 5: return f"hk{code}"
    return f"us{code}"


def _infer_currency(fund_name: str) -> str:
    if any(k in fund_name for k in ["恒生", "港", "HK", "H股"]): return "HKD/CNY"
    if any(k in fund_name for k in ["日", "东京", "东证"]): return "JPY/CNY"
    return "USD/CNY"


def _trigger_holdings_sync(db, redis_client, fund_code):
    sync_key = f"syncing:holdings:{fund_code}"
    if redis_client and not redis_client.get(sync_key):
        redis_client.setex(sync_key, 300, "1")
        threading.Thread(target=update_fund_holdings, args=(db, fund_code,), daemon=True).start()


def _fetch_batch_quotes(secids: list[str]) -> dict[str, dict[str, Any]]:
    quotes = {}
    chunk_size = 60
    for i in range(0, len(secids), chunk_size):
        chunk = secids[i:i+chunk_size]
        url = f"http://qt.gtimg.cn/q={','.join(chunk)}"
        try:
            res = requests.get(url, timeout=5)
            content = res.content.decode('gbk', errors='ignore')
            for line in content.split(';'):
                if '=' not in line: continue
                key, val = line.split('=', 1)
                m_code = key.replace('v_', '').strip()
                parts = val.strip('"').split('~')
                if len(parts) > 32:
                    data = {'price': float(parts[3]), 'change_pct': float(parts[32]), 'name': parts[1]}
                    quotes[parts[2]] = data
                    quotes[m_code] = data
                    if '.' in parts[2] and m_code.startswith('us'):
                        quotes[parts[2].split('.')[0]] = data
        except Exception as e:
            logger.error(f"Quote fetch error: {e}")
    return quotes


def _process_single_fund_batch(db, redis_client, f_code, shadow_map, all_holdings, quotes, industry_map, fund_meta_map, fund_name_map, summary):
    f_name = fund_name_map.get(f_code, f_code)
    f_meta = fund_meta_map.get(f_code, {})

    # Shadow Logic
    if f_code in shadow_map:
        return _calculate_shadow_valuation(db, redis_client, f_code, f_name, f_meta, shadow_map[f_code])

    # Standard Logic
    holdings = all_holdings.get(f_code)
    if not holdings:
        return {"fund_code": f_code, "status": "syncing" if holdings is None else "error"}

    total_impact = 0.0
    total_weight = 0.0
    components = []
    sector_stats = {}

    for h in holdings:
        code = h.get('stock_code') or h.get('code')
        weight = h['weight']
        q = quotes.get(code)
        impact = q['change_pct'] * (weight / 100.0) if q else 0.0
        total_impact += impact
        total_weight += weight

        if not summary:
            # Sector aggregation...
            ind = industry_map.get(code, {'l1': "其他", 'l2': "其他"})
            l1, l2 = ind['l1'], ind['l2']
            if l1 not in sector_stats: sector_stats[l1] = {"impact": 0.0, "weight": 0.0, "sub": {}}
            sector_stats[l1]["impact"] += impact
            sector_stats[l1]["weight"] += weight
            if l2 not in sector_stats[l1]["sub"]: sector_stats[l1]["sub"][l2] = {"impact": 0.0, "weight": 0.0}
            sector_stats[l1]["sub"][l2]["impact"] += impact
            sector_stats[l1]["sub"][l2]["weight"] += weight
            components.append({"code": code, "impact": impact, "weight": weight, "change_pct": q['change_pct'] if q else 0})

    final_est = (total_impact * (100 / total_weight)) if total_weight > 0 else 0.0

    # Post-processing (Bias, FX, Fees)
    bias = db.get_recent_bias(f_code)
    final_est -= bias
    if "QDII" in f_name: final_est += db.get_fx_rate_change(_infer_currency(f_name)) * 0.9

    fee_drag, _, _, _, _ = calculate_fee_drag_pct(f_code, db, f_meta, f_name)
    final_est -= fee_drag

    res = {
        "fund_code": f_code, "fund_name": f_name, "estimated_growth": round(final_est, 4),
        "total_weight": total_weight, "confidence": get_confidence_level(db, f_code, total_weight, f_meta),
        "risk_level": infer_risk_level(f_meta), "timestamp": format_iso8601(datetime.now())
    }
    if not summary:
        res.update({"components": components, "sector_attribution": sector_stats})

    if redis_client: redis_client.setex(f"fund:valuation:{f_code}", 180, json.dumps(res))
    return res
