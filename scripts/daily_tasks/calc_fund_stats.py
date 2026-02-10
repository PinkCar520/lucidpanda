
import os
import sys
import numpy as np
import pandas as pd
import akshare as ak
from datetime import datetime, timedelta

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.logger import logger

class StatsEngine:
    def __init__(self):
        self.db = IntelligenceDB()

    def get_grade_sharpe(self, val):
        if val > 2.0: return 'S'
        if val > 1.2: return 'A'
        if val > 0.5: return 'B'
        return 'C'

    def get_grade_drawdown(self, val):
        abs_val = abs(val)
        if abs_val < 5.0: return 'S'
        if abs_val < 15.0: return 'A'
        if abs_val < 25.0: return 'B'
        return 'C'

    def calculate_for_fund(self, fund_code):
        try:
            logger.info(f"📊 Calculating stats for {fund_code}...")
            # 1. Fetch historical NAV
            df = ak.fund_open_fund_info_em(symbol=fund_code, indicator="单位净值走势")
            if df.empty:
                logger.warning(f"No history for {fund_code}")
                return None

            # df columns: ['净值日期', '单位净值', '日增长率', ...]
            df['date'] = pd.to_datetime(df['净值日期'])
            df = df.sort_values('date')
            df['nav'] = df['单位净值'].astype(float)
            
            # 2. Basic Returns
            latest_nav = df['nav'].iloc[-1]
            
            def get_return(days):
                target_date = df['date'].iloc[-1] - timedelta(days=days)
                start_row = df[df['date'] <= target_date].iloc[-1:]
                if not start_row.empty:
                    start_nav = start_row['nav'].iloc[0]
                    return ((latest_nav - start_nav) / start_nav) * 100
                return 0.0

            ret_1w = get_return(7)
            ret_1m = get_return(30)
            ret_3m = get_return(90)
            ret_1y = get_return(365)

            # 3. Risk Metrics (using 1 year of daily returns)
            one_year_ago = df['date'].iloc[-1] - timedelta(days=365)
            df_year = df[df['date'] >= one_year_ago].copy()
            
            if len(df_year) < 10:
                logger.warning(f"Insufficient history for risk metrics: {fund_code}")
                return None

            # Annualized Volatility
            daily_returns = df_year['nav'].pct_change().dropna()
            vol = daily_returns.std() * np.sqrt(250) * 100 # Annualized %
            
            # Sharpe (Assume 2% risk-free rate)
            rf = 0.02
            annual_ret = (ret_1y / 100)
            sharpe = (annual_ret - rf) / (vol / 100) if vol > 0 else 0
            
            # Max Drawdown
            roll_max = df_year['nav'].cummax()
            drawdown = (df_year['nav'] - roll_max) / roll_max
            max_dd = drawdown.min() * 100 # percentage

            # 4. Sparkline Data (last 30 points, normalized 0-1)
            spark_raw = df['nav'].tail(30).tolist()
            if spark_raw:
                s_min, s_max = min(spark_raw), max(spark_raw)
                if s_max > s_min:
                    spark_norm = [round((v - s_min) / (s_max - s_min), 3) for v in spark_raw]
                else:
                    spark_norm = [0.5] * len(spark_raw)
            else:
                spark_norm = []

            stats = {
                'return_1w': float(ret_1w),
                'return_1m': float(ret_1m),
                'return_3m': float(ret_3m),
                'return_1y': float(ret_1y),
                'volatility': float(vol),
                'sharpe': float(sharpe),
                'sharpe_grade': str(self.get_grade_sharpe(sharpe)),
                'max_dd': float(max_dd),
                'drawdown_grade': str(self.get_grade_drawdown(max_dd)),
                'latest_nav': float(latest_nav),
                'sparkline': [float(v) for v in spark_norm]
            }
            
            self.db.save_fund_stats(fund_code, stats)
            return stats

        except Exception as e:
            logger.error(f"Error calculating stats for {fund_code}: {e}")
            return None

    def run(self):
        # Fetch all funds in watchlists to prioritize
        codes = self.db.get_watchlist_all_codes()
        logger.info(f"🚀 Starting stats calculation for {len(codes)} funds...")
        
        count = 0
        for code in codes:
            self.calculate_for_fund(code)
            count += 1
            
        logger.info(f"✨ Stats calculation finished for {count} funds.")

if __name__ == "__main__":
    engine = StatsEngine()
    engine.run()
