from datetime import date
from typing import Optional, List, Dict, Any
from src.lucidpanda.db.base import DBBase
from src.lucidpanda.core.logger import logger

class FactorService(DBBase):
    """
    负责实体舆情因子的聚合计算 (Factor Indexing)。
    通过对已对齐 canonical_id 的实体进行时序聚合，产出量化因子。
    """
    
    async def update_entity_factor_async(
        self, 
        canonical_id: str, 
        sentiment_score: float, 
        urgency_score: int = 1,
        metric_date: Optional[date] = None
    ):
        """
        异步更新特定实体的每日情绪聚合指标 (Upsert)。
        """
        if metric_date is None:
            metric_date = date.today()

        try:
            conn = self.get_connection()
            with conn:
                cursor = conn.cursor()
                
                query = """
                INSERT INTO entity_metrics (
                    canonical_id, metric_date, sentiment_sum, mention_count, urgency_sum, avg_sentiment, last_updated
                ) VALUES (%s, %s, %s, 1, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (canonical_id, metric_date) DO UPDATE SET
                    sentiment_sum = entity_metrics.sentiment_sum + EXCLUDED.sentiment_sum,
                    mention_count = entity_metrics.mention_count + 1,
                    urgency_sum = entity_metrics.urgency_sum + EXCLUDED.urgency_sum,
                    avg_sentiment = (entity_metrics.sentiment_sum + EXCLUDED.sentiment_sum) / (entity_metrics.mention_count + 1),
                    last_updated = CURRENT_TIMESTAMP;
                """
                
                cursor.execute(query, (
                    canonical_id, 
                    metric_date, 
                    float(sentiment_score), 
                    int(urgency_score), 
                    float(sentiment_score)
                ))
                conn.commit() # 显式提交事务，防止 Proxy 自动回滚
            logger.debug(f"📈 因子聚合成功: {canonical_id} on {metric_date} (score={sentiment_score})")
                
        except Exception as e:
            logger.error(f"❌ 更新实体因子失败 ({canonical_id}): {e}")

    async def get_entity_trend_async(self, canonical_id: str, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取某个实体的历史舆情趋势。
        """
        try:
            conn = self.get_connection()
            with conn:
                cursor = conn.cursor()
                query = """
                SELECT metric_date, avg_sentiment, mention_count, urgency_sum
                FROM entity_metrics
                WHERE canonical_id = %s AND metric_date > CURRENT_DATE - INTERVAL '%s day'
                ORDER BY metric_date ASC;
                """
                cursor.execute(query, (canonical_id, days))
                results = cursor.fetchall()
                return results
        except Exception as e:
            logger.error(f"❌ 获取实体趋势失败 ({canonical_id}): {e}")
            return []
