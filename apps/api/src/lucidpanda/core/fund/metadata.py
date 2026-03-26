import json
import logging
import re
from typing import Any

import akshare as ak

logger = logging.getLogger(__name__)


def identify_shadow_etf(db: Any, fund_code: str, fund_name: str) -> str | None:
    """
    Heuristic algorithm to find parent ETF for feeder funds.
    Example: '永赢中证全指医疗器械ETF发起联接C' -> '中证全指医疗器械ETF' -> '159883'
    """
    if not fund_name or "联接" not in fund_name:
        return None

    # 1. Clean the name to find the core ETF name
    core_name = fund_name
    patterns = [r'发起式联接', r'发起联接', r'联接', r'[A-Z]$', r'\(.*?\)', r'（.*?）']
    for p in patterns:
        core_name = re.sub(p, '', core_name)
    core_name = core_name.strip()

    if not core_name:
        return None

    logger.info(f"🧩 Feeder Detected: '{fund_name}' -> Core: '{core_name}'")

    # 2. Search local DB for this core name in fund_metadata
    try:
        conn = db.get_connection()
        # Use standard psycopg interface as in the original code
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT fund_code FROM fund_metadata
                WHERE (fund_name = %s OR fund_name LIKE %s)
                AND (fund_code LIKE '51%%' OR fund_code LIKE '15%%' OR fund_code LIKE '56%%' OR fund_code LIKE '58%%')
                LIMIT 1
            """, (core_name, f"%{core_name}%"))
            row = cursor.fetchone()
            if row:
                parent_code = row[0]
                logger.info(f"🎯 Shadow Found: '{fund_name}' -> Parent ETF: {parent_code}")
                db.save_fund_relationship(fund_code, parent_code, "ETF_FEEDER")
                return parent_code
    except Exception as e:
        logger.error(f"Shadow identification DB error: {e}")
    finally:
        if 'conn' in locals() and conn:
            conn.close()

    return None


def identify_index_proxy(db: Any, fund_code: str, fund_name: str) -> tuple[str | None, float]:
    """Heuristic to map passive index funds to benchmark market indices."""
    if not fund_name or "指数" not in fund_name:
        return None, 0.95

    if "增强" in fund_name:
        return None, 0.95

    # Registry of common indices
    INDEX_REGISTRY = {
        "沪深300": "sh000300",
        "中证500": "sh000905",
        "中证1000": "sh000852",
        "上证50": "sh000016",
        "创业板": "sz399006",
        "科创50": "sh000688",
        "科创100": "sh000698",
        "恒生指数": "hkHSI",
        "恒生科技": "hkHSTECH",
        "纳斯达克100": "sh513100",
        "纳斯达克": "sh513100",
        "标普500": "sh513500",
        "医疗器械": "sz159883",
        "中证白酒": "sz161725",
        "半导体": "sh512480",
        "芯片": "sh512760",
        "红利": "sh000015",
        "恒生互联网": "sh513330"
    }

    for keyword, index_code in INDEX_REGISTRY.items():
        if keyword in fund_name:
            logger.info(f"📊 Index Proxy Match: '{fund_name}' -> Index: {keyword} ({index_code})")
            db.save_fund_relationship(fund_code, index_code, "INDEX_PROXY", ratio=0.95)
            return index_code, 0.95

    return None, 0.95


def get_fund_name(db: Any, redis_client: Any, fund_code: str) -> str:
    """Fetch Fund Name with Redis Cache and Local DB fallback."""
    if redis_client:
        cached_name = redis_client.get(f"fund:name:{fund_code}")
        if cached_name:
            return cached_name

    fund_name = ""
    try:
        names = db.get_fund_names([fund_code])
        if names.get(fund_code):
            fund_name = names[fund_code]

        if not fund_name:
            import os
            # Disable proxy for individual fetch
            orig_http = os.environ.get('HTTP_PROXY')
            orig_https = os.environ.get('HTTPS_PROXY')
            if orig_http: del os.environ['HTTP_PROXY']
            if orig_https: del os.environ['HTTPS_PROXY']

            try:
                info_df = ak.fund_individual_basic_info_xq(symbol=fund_code)
                fund_name = info_df[info_df.iloc[:,0] == '基金简称'].iloc[0,1]
            finally:
                if orig_http: os.environ['HTTP_PROXY'] = orig_http
                if orig_https: os.environ['HTTPS_PROXY'] = orig_https

        if redis_client and fund_name:
            redis_client.setex(f"fund:name:{fund_code}", 86400 * 7, fund_name)

    except Exception:
        pass
    return fund_name or fund_code


def get_industry_map(db: Any, redis_client: Any, stock_codes: list[str]) -> dict[str, dict[str, str]]:
    """Fetch industry mapping (L1 & L2) for a list of stocks."""
    if not stock_codes:
        return {}
    if not redis_client:
        return {}

    try:
        raw_data = redis_client.hmget("stock:industry:full", stock_codes)
        result = {}
        missing_codes = []

        for code, raw_json in zip(stock_codes, raw_data, strict=False):
            if raw_json:
                try:
                    result[code] = json.loads(raw_json)
                except Exception:
                    missing_codes.append(code)
            else:
                missing_codes.append(code)

        if not missing_codes:
            return result

        if missing_codes:
            conn = db.get_connection()
            try:
                pipeline = redis_client.pipeline()
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT stock_code, industry_l1_name, industry_l2_name
                        FROM stock_metadata
                        WHERE stock_code = ANY(%s)
                    """, (missing_codes,))
                    rows = cursor.fetchall()

                    db_updates = {}
                    for r in rows:
                        val = {'l1': r[1] or "其他", 'l2': r[2] or "其他"}
                        db_updates[r[0]] = json.dumps(val)
                        result[r[0]] = val

                    if db_updates:
                        pipeline.hset("stock:industry:full", mapping=db_updates)

                    unknowns = set(missing_codes) - set(result.keys())
                    if unknowns:
                         unknown_val = {'l1': "其他", 'l2': "其他"}
                         unknown_json = json.dumps(unknown_val)
                         unknown_map = dict.fromkeys(unknowns, unknown_json)
                         pipeline.hset("stock:industry:full", mapping=unknown_map)
                         for c in unknowns:
                             result[c] = unknown_val
                pipeline.execute()
            finally:
                conn.close()

        return result
    except Exception as e:
        logger.error(f"Industry map fetch failed: {e}")
        return {}


def infer_risk_level(fund_meta: dict[str, Any]) -> str:
    """Synthetic Risk Rating (SRR)."""
    db_risk = fund_meta.get('risk_level')
    if db_risk and db_risk.startswith('R'):
        return db_risk

    f_type = str(fund_meta.get('type', ''))
    if any(k in f_type for k in ["货币", "理财", "避险"]):
        return "R1"
    if any(k in f_type for k in ["短债", "长债", "纯债", "一级"]):
        return "R2"
    if any(k in f_type for k in ["偏债", "混合二级", "平衡", "灵活"]):
        return "R3"
    if any(k in f_type for k in ["偏股", "普通股票", "标准指数", "指数型-股票", "Reits"]):
        return "R4"
    if any(k in f_type for k in ["QDII", "商品", "分级", "海外股票", "进取型"]):
        return "R5"
    return "R3"


def get_confidence_level(db: Any, fund_code: str, current_weight: float, fund_meta: dict[str, Any]) -> dict[str, Any]:
    """Calculates a weighted confidence score."""
    perf = db.get_fund_performance_metrics(fund_code, days=7)
    mae = perf['avg_mae']
    acc_score = 0
    reasons = []

    recent_history = db.get_recent_tracking_statuses(fund_code, limit=3)
    is_suspected_rebalance = False
    if len(recent_history) >= 3:
        not_precise = all(h['status'] != 'S' for h in recent_history)
        avg_drift = sum(abs(h['deviation']) for h in recent_history) / 3
        if not_precise and avg_drift > 0.6:
            is_suspected_rebalance = True
            reasons.append("portfolio_drift")

    if mae is None:
        acc_score = 40
        reasons.append("new_fund")
    elif mae < 0.2:
        acc_score = 60
        reasons.append("accuracy_high")
    elif mae < 0.5:
        acc_score = 45
        reasons.append("accuracy_medium")
    elif mae < 1.0:
        acc_score = 20
        reasons.append("accuracy_low")
    else:
        acc_score = 0
        reasons.append("accuracy_poor")

    cov_score = 0
    if current_weight >= 90:
        cov_score = 30
        reasons.append("coverage_full")
    elif current_weight >= 70:
        cov_score = 20
        reasons.append("coverage_high")
    elif current_weight >= 40:
        cov_score = 10
        reasons.append("coverage_partial")
    else:
        cov_score = 0
        reasons.append("coverage_low")

    type_score = 10
    f_type = str(fund_meta.get('type', ''))
    if "QDII" in f_type:
        type_score = 5
        reasons.append("qdii_lag")
    if "FOF" in f_type:
        type_score = 0
        reasons.append("fof_complexity")

    final_score = acc_score + cov_score + type_score
    if is_suspected_rebalance:
        final_score = max(0, final_score - 30)

    level = "medium"
    if final_score >= 80:
        level = "high"
    elif final_score < 50:
        level = "low"

    return {
        "level": level,
        "score": final_score,
        "is_suspected_rebalance": is_suspected_rebalance,
        "reasons": reasons
    }
