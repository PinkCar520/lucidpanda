import os
import logging
from datetime import datetime
from typing import Any

import akshare as ak
import pandas as pd

logger = logging.getLogger(__name__)


def update_fund_holdings(db: Any, fund_code: str) -> list[dict[str, Any]]:
    """Fetch latest holdings from Market Provider and save to DB."""
    logger.info(f"🔍 Fetching holdings for fund: {fund_code}")

    # Temporary disable proxy for data fetching
    original_http = os.environ.get('HTTP_PROXY')
    original_https = os.environ.get('HTTPS_PROXY')
    os.environ['HTTP_PROXY'] = ''
    os.environ['HTTPS_PROXY'] = ''

    try:
        # 1. Try last year first (most common case)
        last_year = str(datetime.now().year - 1)
        try:
            df = ak.fund_portfolio_hold_em(symbol=fund_code, date=last_year)
        except Exception:
            df = pd.DataFrame()

        if df.empty:
            current_year = str(datetime.now().year)
            try:
                df = ak.fund_portfolio_hold_em(symbol=fund_code, date=current_year)
            except Exception:
                pass

        if df.empty:
            logger.warning(f"No holdings found for {fund_code}")
            return []

        # 2. Sort by quarter to get truly latest
        all_quarters = df['季度'].unique()
        if len(all_quarters) == 0:
            return []

        latest_quarter = sorted(all_quarters, reverse=True)[0]
        logger.info(f"📅 Latest Report: {latest_quarter}")

        latest_df = df[df['季度'] == latest_quarter]

        holdings = []
        for _, row in latest_df.iterrows():
            holdings.append({
                'code': str(row['股票代码']),
                'name': str(row['股票名称']),
                'weight': float(row['占净值比例']),
                'report_date': latest_quarter
            })

        # Save to DB
        db.save_fund_holdings(fund_code, holdings)
        return holdings

    except Exception as e:
        logger.error(f"Update Holdings Failed: {e}")
        return []
    finally:
        # Restore proxy if needed
        if original_http:
            os.environ['HTTP_PROXY'] = original_http
        if original_https:
            os.environ['HTTPS_PROXY'] = original_https
