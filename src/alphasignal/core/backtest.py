import yfinance as yf
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

    def sync_outcomes(self):
        """
        [自动回填] 检查旧数据并更新 T+1h, T+24h 的价格
        采用 "Next Trading Candle" 逻辑，确保对齐交易时段。
        """
        now = datetime.now(pytz.utc)
        # 频率控制：如果距离上次尝试不足冷却时间，直接跳过
        if (now - self.last_sync_attempt).total_seconds() < self.sync_cooldown_minutes * 60:
            return

        pending_records = self.db.get_pending_outcomes()
        if not pending_records:
            return

        # 预解析并过滤
        ready_records = []
        for record in pending_records:
            try:
                raw_time = record['timestamp']
                if isinstance(raw_time, str):
                    try:
                        dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        dt = datetime.strptime(raw_time, "%Y-%m-%d %H:%M:%S.%f%z")
                else:
                    dt = raw_time
                
                if dt.tzinfo is None:
                    dt = pytz.utc.localize(dt)
                else:
                    dt = dt.astimezone(pytz.utc)
                
                # 只处理 15 分钟以前的记录，避免雅虎还没生成最近的 Candle
                if (now - dt).total_seconds() > 900:
                    ready_records.append((record, dt))
            except:
                continue

        if not ready_records:
            return

        logger.info(f"⏳ 正在同步 {len(ready_records)} 条历史数据的收益率...")
        self.last_sync_attempt = now

        # 1. 确定所需的历史数据范围
        min_time = min(r[1] for r in ready_records)
        max_time = max(r[1] for r in ready_records)

        # 2. 获取历史数据 (缓冲缩小为 2 天以减少数据量)
        fetch_start = (min_time - timedelta(days=2)).strftime('%Y-%m-%d')
        fetch_end = (max_time + timedelta(days=2)).strftime('%Y-%m-%d')
        
        logger.info(f"📈 获取行情数据范围: {fetch_start} 至 {fetch_end}")
        
        try:
            ticker = yf.Ticker("GC=F")
            hist = ticker.history(start=fetch_start, end=fetch_end, interval="1h")
            
            if hist.empty:
                logger.warning("未能获取到行情数据，跳过本次同步")
                return

            if hist.index.tz is None:
                hist.index = hist.index.tz_localize('UTC')
            else:
                hist.index = hist.index.tz_convert('UTC')
                
            # 同步成功，恢复较短的冷却时间
            self.sync_cooldown_minutes = 15
                
        except Exception as e:
            if "Too Many Requests" in str(e) or "429" in str(e):
                logger.error("🚫 Yahoo Finance 限流，进入 60 分钟冷却保护期")
                self.sync_cooldown_minutes = 60
            else:
                logger.warning(f"获取历史行情失败: {e}")
            return

        # 3. 逐条匹配 (Next Trading Candle)
        success_count = 0
        for record, record_time in ready_records:
            try:
                windows = {
                    'price_15m': timedelta(minutes=15),
                    'price_1h': timedelta(hours=1),
                    'price_4h': timedelta(hours=4),
                    'price_12h': timedelta(hours=12),
                    'price_24h': timedelta(hours=24)
                }
                
                outcomes = {}
                for col, delta in windows.items():
                    target_time = record_time + delta
                    idx = hist.index.searchsorted(target_time)
                    
                    if idx < len(hist):
                        matched_time = hist.index[idx]
                        if (matched_time - target_time).total_seconds() <= 4 * 86400:
                            outcomes[col] = round(float(hist.iloc[idx]['Close']), 2)

                if outcomes:
                    self.db.update_outcome(record['id'], **outcomes)
                    success_count += 1
                
            except Exception as e:
                logger.warning(f"单条回填失败 ID {record['id']}: {e}")
        
        logger.info(f"✅ 同步完成: 成功回填 {success_count}/{len(ready_records)} 条")

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