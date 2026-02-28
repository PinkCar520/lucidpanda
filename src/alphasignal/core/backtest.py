import akshare as ak
import pandas as pd
from datetime import datetime, timedelta
import pytz
import psycopg2
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.core.database import IntelligenceDB


class BacktestEngine:
    def __init__(self, db: IntelligenceDB):
        self.db = db
        self.current_position = None # Initial state: No position (None)
        self.last_sync_attempt = datetime.min.replace(tzinfo=pytz.utc)
        self.sync_cooldown_minutes = 15 # Initial cooldown

    def process_signal(self, signal_direction: str) -> bool:
        """
        处理交易信号并应用日内同向去重逻辑。
        Args:
            signal_direction (str): 新的信号方向，'Long' 或 'Short'。
        Returns:
            bool: 如果根据去重规则开仓或反转仓位，则返回 True；否则返回 False (信号被跳过)。
        """
        if signal_direction not in ['Long', 'Short']:
            logger.warning(f"未知信号方向: {signal_direction}，跳过处理。")
            return False

        trade_initiated = False

        if signal_direction == 'Long':
            if self.current_position in [None, 'Short']:
                logger.info(f"➡️ 新信号: Long. 当前持仓: {self.current_position}. 开多仓。")
                self.current_position = 'Long'
                trade_initiated = True
            elif self.current_position == 'Long':
                logger.info("🚫 新信号: Long. 当前持仓: Long. 同向信号，跳过。")
                trade_initiated = False
        elif signal_direction == 'Short':
            if self.current_position in [None, 'Long']:
                logger.info(f"➡️ 新信号: Short. 当前持仓: {self.current_position}. 开空仓。")
                self.current_position = 'Short'
                trade_initiated = True
            elif self.current_position == 'Short':
                logger.info("🚫 新信号: Short. 当前持仓: Short. 同向信号，跳过。")
                trade_initiated = False
        
        return trade_initiated

    def _fetch_precise_hist(self) -> pd.DataFrame:
        """
        核心数据抓取：优先抓取东方财富(COMEX GC)，失败则降级抓取上海金(AU)作为影子参考。
        """
        import requests
        
        # --- 方案 A: 东方财富 (COMEX GC 15m) ---
        # secid=101.GC00Y, klt=15 (15分钟), lmt=800 (覆盖约8天历史)
        em_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid=101.GC00Y&ut=fa5fd1943c0a30548d390f18a2cd7645&fields1=f1,f2,f3,f4,f5&fields2=f51,f52,f53,f54,f55,f56,f57,f58&klt=15&fqt=0&end=20261231&lmt=800"
        try:
            resp = requests.get(em_url, timeout=10)
            data = resp.json()
            if data and 'data' in data and data['data']['klines']:
                klines = data['data']['klines']
                rows = [k.split(',') for k in klines]
                df = pd.DataFrame(rows, columns=['datetime', 'open', 'close', 'high', 'low', 'vol', 'amt', 'pct'])
                
                # 时间轴转换：东财是北京时间 (GMT+8)
                df['timestamp'] = pd.to_datetime(df['datetime']).dt.tz_localize('Asia/Shanghai').dt.tz_convert('UTC')
                df['Close'] = pd.to_numeric(df['close'])
                logger.info(f"📈 成功从 EastMoney 获取 {len(df)} 条 15m 精度数据 (COMEX GC)")
                return df.set_index('timestamp')[['Close']]
        except Exception as e:
            logger.warning(f"EastMoney 接口异常: {e}，尝试影子数据预案...")

        # --- 方案 B: 影子指标 (Shanghai Gold au0 15m) ---
        try:
            df_au = ak.futures_zh_minute_sina(symbol='au0', period='15')
            if not df_au.empty:
                df_au['datetime'] = pd.to_datetime(df_au['datetime']).dt.tz_localize('Asia/Shanghai').dt.tz_convert('UTC')
                df_au = df_au.rename(columns={'close': 'Close', 'datetime': 'timestamp'})
                logger.info(f"⚠️ 使用影子指标(上海金)回填，注意存在汇率压差！条数: {len(df_au)}")
                return df_au.set_index('timestamp')[['Close']]
        except Exception as e:
            logger.error(f"所有分时数据源均失效: {e}")
        
        return pd.DataFrame()

    def sync_outcomes(self):
        """
        [自动回填] 升级为高精度 15m 级别回填
        解决原日线数据导致的收益率失真问题。
        """
        now = datetime.now(pytz.utc)
        if (now - self.last_sync_attempt).total_seconds() < self.sync_cooldown_minutes * 60:
            return

        pending_records = self.db.get_pending_outcomes()
        if not pending_records:
            return

        ready_records = []
        for record in pending_records:
            try:
                dt = pd.to_datetime(record['timestamp'])
                if dt.tzinfo is None: dt = pytz.utc.localize(dt)
                
                # 至少给 15-30 分钟缓冲时间，等 K 线固化
                if (now - dt).total_seconds() > 1800:
                    ready_records.append((record, dt))
            except:
                continue

        if not ready_records:
            return

        logger.info(f"⏳ 正在执行高精度收益率回填，目标条数: {len(ready_records)}")
        self.last_sync_attempt = now

        # 获取精确 15m 历史轴
        hist = self._fetch_precise_hist()
        if hist.empty:
            return

        # 逐条对齐
        success_count = 0
        windows = {
            'price_15m': timedelta(minutes=15),
            'price_1h':  timedelta(hours=1),
            'price_4h':  timedelta(hours=4),
            'price_12h': timedelta(hours=12),
            'price_24h': timedelta(hours=24)
        }

        for record, record_time in ready_records:
            try:
                outcomes = {}
                for col, delta in windows.items():
                    target_time = record_time + delta
                    # 在 15m 轴里找最近的一根 K 线
                    idx = hist.index.searchsorted(target_time)
                    
                    if idx < len(hist):
                        matched_time = hist.index[idx]
                        # 容错：如果匹配到的时间距离目标超过 3 天（长假休市），则判定为无效
                        if (matched_time - target_time).total_seconds() <= 3 * 86400:
                            outcomes[col] = round(float(hist.iloc[idx]['Close']), 2)

                if outcomes:
                    self.db.update_outcome(record['id'], **outcomes)
                    success_count += 1
                
            except Exception as e:
                logger.warning(f"单条回填失败 ID {record['id']}: {e}")
        
        logger.info(f"✅ 高精度同步完成: 成功处理 {success_count}/{len(ready_records)} 条")

    def get_confidence_stats(self, keyword):
        """
        [策略执行] 根据关键词查询历史表现
        """
        try:
            with psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                dbname=settings.POSTGRES_DB
            ) as conn:
                with conn.cursor() as cursor:
                    query = """
                        SELECT gold_price_snapshot, price_1h 
                        FROM intelligence 
                        WHERE (content ILIKE %s OR summary::text ILIKE %s) 
                        AND price_1h IS NOT NULL
                    """
                    pattern = f"%{keyword}%"
                    cursor.execute(query, (pattern, pattern))
                    rows = cursor.fetchall()

            if not rows:
                return None

            total = len(rows)
            up_count = 0
            total_return = 0

            for start_price, end_price in rows:
                if not start_price or not end_price:
                    continue
                
                ret = (end_price - start_price) / start_price * 100
                total_return += ret
                if ret > 0:
                    up_count += 1
            
            if total == 0:
                return None

            return {
                "count": total,
                "win_rate": round(up_count / total * 100, 1),
                "avg_return": round(total_return / total, 2)
            }
        except Exception as e:
            logger.error(f"Error calculating confidence stats: {e}")
            return None