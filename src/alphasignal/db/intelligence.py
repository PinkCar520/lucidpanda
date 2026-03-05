"""
db/intelligence.py — 情报域
============================
情报 CRUD、去重（URL/pg_trgm/pgvector）、向量嵌入、信源可信度。
"""
from datetime import datetime, timedelta
import pytz
import psycopg2
from psycopg2.extras import Json, DictCursor
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.db.base import DBBase


class IntelligenceRepo(DBBase):

    # ── pgvector 语义去重 ─────────────────────────────────────────────────

    def is_semantic_duplicate(self, vector, threshold: float = 0.85) -> bool:
        """查询 pgvector，判断向量是否与历史情报语义重复（HNSW, O(log n)）。"""
        try:
            vec_list = vector.tolist() if hasattr(vector, 'tolist') else list(vector)
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM intelligence
                WHERE embedding_vec IS NOT NULL
                  AND 1 - (embedding_vec <=> %s::vector) > %s
                LIMIT 1
            """, (vec_list, threshold))
            row = cursor.fetchone()
            conn.close()
            return row is not None
        except Exception as e:
            logger.warning(f"⚠️ pgvector 语义查询失败，降级为非重复: {e}")
            return False

    def save_embedding_vec(self, source_id: str, vector) -> None:
        """将 BERT 嵌入向量持久化到 intelligence 表的 embedding_vec 列。"""
        try:
            vec_list = vector.tolist() if hasattr(vector, 'tolist') else list(vector)
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE intelligence
                SET embedding_vec = %s::vector
                WHERE source_id = %s
            """, (vec_list, source_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning(f"⚠️ 嵌入向量写入失败 [{source_id}]: {e}")

    # ── 信源可信度 ────────────────────────────────────────────────────────

    def compute_source_credibility(self) -> dict:
        """
        计算各信源的历史预测准确率，并将结果回填到 source_credibility_score 列。
        调用时机：BacktestEngine.sync_outcomes() 之后。
        返回：{source_name: accuracy_float}
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT
                    source_name,
                    COUNT(*) AS total,
                    SUM(CASE
                        WHEN sentiment_score > 0.2 AND price_1h > gold_price_snapshot THEN 1
                        WHEN sentiment_score < -0.2 AND price_1h < gold_price_snapshot THEN 1
                        ELSE 0
                    END) AS correct
                FROM intelligence
                WHERE source_name IS NOT NULL
                  AND sentiment_score IS NOT NULL
                  AND price_1h IS NOT NULL
                  AND gold_price_snapshot IS NOT NULL
                  AND ABS(sentiment_score) > 0.2
                GROUP BY source_name
                HAVING COUNT(*) >= 5
            """)
            rows = cursor.fetchall()
            credibility_map = {}
            for row in rows:
                source = row['source_name']
                accuracy = round(row['correct'] / row['total'], 4) if row['total'] > 0 else None
                credibility_map[source] = accuracy

            for source_name, score in credibility_map.items():
                cursor.execute("""
                    UPDATE intelligence
                    SET source_credibility_score = %s
                    WHERE source_name = %s
                      AND source_credibility_score IS DISTINCT FROM %s
                """, (score, source_name, score))
            conn.commit()
            conn.close()

            if credibility_map:
                top = sorted(credibility_map.items(), key=lambda x: x[1] or 0, reverse=True)
                logger.info(
                    f"📊 信源可信度更新完成 | 共 {len(credibility_map)} 个信源 | "
                    f"Top3: {[(s, f'{a:.1%}') for s, a in top[:3]]}"
                )
            return credibility_map
        except Exception as e:
            logger.error(f"❌ 信源可信度计算失败: {e}")
            return {}

    def get_source_credibility_report(self) -> list:
        """查询各信源可信度排名，供监控/API 使用。"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT
                    source_name,
                    ROUND(AVG(source_credibility_score)::numeric, 4) AS accuracy,
                    COUNT(*) AS total_signals
                FROM intelligence
                WHERE source_name IS NOT NULL
                  AND source_credibility_score IS NOT NULL
                GROUP BY source_name
                ORDER BY accuracy DESC
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            logger.error(f"❌ 获取信源报告失败: {e}")
            return []

    # ── Outcome 回填 ──────────────────────────────────────────────────────

    def update_outcome(self, record_id, **kwargs):
        """Update historical outcome data dynamically."""
        if not kwargs:
            return
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            columns = []
            values = []
            for col, val in kwargs.items():
                if val is not None:
                    columns.append(f"{col} = %s")
                    values.append(val)
            if columns:
                query = f"UPDATE intelligence SET {', '.join(columns)} WHERE id = %s"
                values.append(record_id)
                cursor.execute(query, tuple(values))
                conn.commit()
                logger.info(f"✅ Outcome Updated ID: {record_id} | Fields: {list(kwargs.keys())}")
            conn.close()
        except Exception as e:
            logger.error(f"Update Outcome Failed: {e}")

    def get_pending_outcomes(self):
        """Get records older than 1 hour that lack any of the outcome prices."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT * FROM intelligence
                WHERE (price_1h IS NULL OR price_15m IS NULL OR price_4h IS NULL OR price_12h IS NULL)
                AND timestamp < NOW() - INTERVAL '1 hour'
                ORDER BY timestamp DESC LIMIT 50
            """)
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Pending Outcomes Failed: {e}")
            return []

    # ── 情报写入 ──────────────────────────────────────────────────────────

    def save_raw_intelligence(self, raw_data):
        """Save raw intelligence data immediately (before analysis)."""
        try:
            news_time = None
            if raw_data.get('timestamp'):
                import dateutil.parser, calendar
                try:
                    if isinstance(raw_data['timestamp'], str):
                        news_time = dateutil.parser.parse(raw_data['timestamp'])
                    elif hasattr(raw_data['timestamp'], 'tm_year'):
                        ts_utc = calendar.timegm(raw_data['timestamp'])
                        news_time = datetime.fromtimestamp(ts_utc, tz=pytz.utc)
                except Exception as e:
                    logger.warning(f"Timestamp parsing failed: {e}")

            if news_time is None:
                news_time = datetime.now(pytz.utc)
            else:
                if news_time.tzinfo is None:
                    news_time = pytz.utc.localize(news_time)
                else:
                    news_time = news_time.astimezone(pytz.utc)

            market_session = self.get_market_session(news_time)
            clustering_score, exhaustion_score = self.get_advanced_metrics(news_time, raw_data.get('content'))

            dxy = raw_data.get('dxy_snapshot')
            if dxy is None: dxy = self.get_market_snapshot("DX-Y.NYB", news_time)
            us10y = raw_data.get('us10y_snapshot')
            if us10y is None: us10y = self.get_market_snapshot("^TNX", news_time)
            gvz = raw_data.get('gvz_snapshot')
            if gvz is None: gvz = self.get_market_snapshot("^GVZ", news_time)
            gold = raw_data.get('gold_price_snapshot')
            if gold is None: gold = self.get_market_snapshot("GC=F", news_time)

            conn = self._get_conn()
            cursor = conn.cursor()

            embedding_binary = None
            if 'embedding' in raw_data and raw_data['embedding'] is not None:
                import pickle
                embedding_binary = psycopg2.Binary(pickle.dumps(raw_data['embedding']))

            cursor.execute("""
                INSERT INTO intelligence (
                    source_id, author, content, url, timestamp,
                    market_session, clustering_score, exhaustion_score,
                    dxy_snapshot, us10y_snapshot, gvz_snapshot, gold_price_snapshot,
                    fed_regime, embedding, source_name
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO UPDATE SET
                    author = EXCLUDED.author
                RETURNING id
            """, (
                raw_data.get('id'),
                raw_data.get('author'),
                raw_data.get('original_content') if raw_data.get('original_content') else raw_data.get('content'),
                raw_data.get('url'),
                news_time,
                market_session,
                clustering_score,
                float(exhaustion_score),
                float(dxy) if dxy is not None else None,
                float(us10y) if us10y is not None else None,
                float(gvz) if gvz is not None else None,
                float(gold) if gold is not None else None,
                float(raw_data.get('fed_val', 0.0)),
                embedding_binary,
                raw_data.get('source'),
            ))
            row = cursor.fetchone()
            conn.commit()
            conn.close()
            return row[0] if row else None
        except Exception as e:
            logger.error(f"Save Raw Failed: {e}")
            return None

    def update_intelligence_analysis(self, source_id, analysis_result, raw_data):
        """Update a record with analysis results."""
        try:
            sentiment_score = analysis_result.get('sentiment_score', 0)
            orig_score = sentiment_score
            fed_val = raw_data.get('fed_val', 0)
            macro_adj = 0.0
            if fed_val > 0:
                macro_adj = 0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score + 0.15))
                logger.info(f"⚖️  Dimension D 权调节 (Dovish/+0.15): {orig_score:.2f} -> {sentiment_score:.2f}")
            elif fed_val < 0:
                macro_adj = -0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score - 0.15))
                logger.info(f"⚖️  Dimension D 权调节 (Hawkish/-0.15): {orig_score:.2f} -> {sentiment_score:.2f}")

            def to_jsonb(val):
                return Json(val)

            conn = self._get_conn()
            cursor = conn.cursor()
            embedding_binary = None
            if 'embedding' in analysis_result and analysis_result['embedding'] is not None:
                import pickle
                embedding_binary = psycopg2.Binary(pickle.dumps(analysis_result['embedding']))

            cursor.execute("""
                UPDATE intelligence SET
                    summary = %s, sentiment = %s, urgency_score = %s,
                    market_implication = %s, actionable_advice = %s,
                    sentiment_score = %s, macro_adjustment = %s,
                    embedding = COALESCE(%s, embedding),
                    status = 'COMPLETED', last_error = NULL
                WHERE source_id = %s
            """, (
                to_jsonb(analysis_result.get('summary')),
                to_jsonb(analysis_result.get('sentiment')),
                analysis_result.get('urgency_score'),
                to_jsonb(analysis_result.get('market_implication')),
                to_jsonb(analysis_result.get('actionable_advice')),
                float(sentiment_score), float(macro_adj),
                embedding_binary, source_id,
            ))
            conn.commit()
            conn.close()
            logger.info(f"💾 Updated Analysis for ID: {source_id}")
        except Exception as e:
            logger.error(f"Update Analysis Failed: {e}")

    def save_intelligence(self, raw_data, analysis_result, gold_price_snapshot=None, price_1h=None, price_24h=None):
        """Save fully-analyzed intelligence to PostgreSQL using JSONB."""
        try:
            news_time = None
            if raw_data.get('timestamp'):
                import dateutil.parser, calendar
                try:
                    if isinstance(raw_data['timestamp'], str):
                        news_time = dateutil.parser.parse(raw_data['timestamp'])
                    elif hasattr(raw_data['timestamp'], 'tm_year'):
                        ts_utc = calendar.timegm(raw_data['timestamp'])
                        news_time = datetime.fromtimestamp(ts_utc, tz=pytz.utc)
                except Exception as e:
                    logger.warning(f"Failed to parse timestamp: {e}")

            market_session = self.get_market_session(news_time)
            clustering_score, exhaustion_score = self.get_advanced_metrics(news_time, raw_data.get('content'))

            if news_time is None:
                news_time = datetime.now(pytz.utc)
            else:
                if news_time.tzinfo is None:
                    news_time = pytz.utc.localize(news_time)
                else:
                    news_time = news_time.astimezone(pytz.utc)

            if gold_price_snapshot is None:
                gold_price_snapshot = self.get_market_snapshot("GC=F", news_time)
            dxy = raw_data.get('dxy_snapshot') or self.get_market_snapshot("DX-Y.NYB", news_time)
            us10y = raw_data.get('us10y_snapshot') or self.get_market_snapshot("^TNX", news_time)
            gvz = raw_data.get('gvz_snapshot') or self.get_market_snapshot("^GVZ", news_time)

            sentiment_score = analysis_result.get('sentiment_score', 0)
            orig_score = sentiment_score
            fed_val = raw_data.get('fed_val', 0)
            macro_adj = 0.0
            if fed_val > 0:
                macro_adj = 0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score + 0.15))
            elif fed_val < 0:
                macro_adj = -0.15
                sentiment_score = max(-1.0, min(1.0, sentiment_score - 0.15))

            def to_jsonb(val):
                return Json(val)

            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO intelligence (
                    source_id, author, content, summary, sentiment,
                    urgency_score, market_implication, actionable_advice, url,
                    gold_price_snapshot, price_1h, price_24h, timestamp, market_session,
                    clustering_score, exhaustion_score, dxy_snapshot, us10y_snapshot, gvz_snapshot,
                    sentiment_score, fed_regime, macro_adjustment
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (source_id) DO NOTHING
            """, (
                raw_data.get('id'), raw_data.get('author'), raw_data.get('content'),
                to_jsonb(analysis_result.get('summary')), to_jsonb(analysis_result.get('sentiment')),
                analysis_result.get('urgency_score'),
                to_jsonb(analysis_result.get('market_implication')),
                to_jsonb(analysis_result.get('actionable_advice')),
                raw_data.get('url'),
                float(gold_price_snapshot) if gold_price_snapshot is not None else None,
                float(price_1h) if price_1h is not None else None,
                float(price_24h) if price_24h is not None else None,
                news_time, market_session, clustering_score,
                float(exhaustion_score) if exhaustion_score is not None else 0.0,
                float(dxy) if dxy is not None else None,
                float(us10y) if us10y is not None else None,
                float(gvz) if gvz is not None else None,
                float(sentiment_score),
                float(fed_val) if fed_val is not None else 0.0,
                float(macro_adj),
            ))
            conn.commit()
            if cursor.rowcount > 0:
                logger.info(f"💾 Saved Intelligence | Gold: ${gold_price_snapshot}")
            conn.close()
        except Exception as e:
            logger.error(f"Save Intelligence Failed: {e}")

    # ── 查询方法 ──────────────────────────────────────────────────────────

    def source_id_exists(self, source_id: str) -> bool:
        """O(1) 查询：source_id 是否已在 intelligence 表中。"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM intelligence WHERE source_id = %s LIMIT 1", (source_id,))
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except Exception as e:
            logger.warning(f"source_id_exists 查询失败，默认返回 False: {e}")
            return False

    def source_ids_batch_exists(self, source_ids: list) -> set:
        """批量查询一组 source_id 是否已存在，返回已存在的 ID 集合。"""
        if not source_ids:
            return set()
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT source_id FROM intelligence WHERE source_id = ANY(%s)", (source_ids,))
            rows = cursor.fetchall()
            conn.close()
            return {row[0] for row in rows}
        except Exception as e:
            logger.warning(f"source_ids_batch_exists 查询失败，返回空集合: {e}")
            return set()

    def get_recent_intelligence(self, limit=10):
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("SELECT * FROM intelligence ORDER BY timestamp DESC LIMIT %s", (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Recent Failed: {e}")
            return []

    def get_pending_intelligence(self, limit=20):
        """Fetch records that need AI analysis or retries."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT * FROM intelligence
                WHERE status IN ('PENDING', 'FAILED')
                ORDER BY timestamp DESC LIMIT %s
            """, (limit,))
            rows = cursor.fetchall()
            conn.close()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Pending Failed: {e}")
            return []

    def update_intelligence_status(self, source_id, status, error=None):
        """Update the lifecycle status of an intelligence item."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE intelligence SET status = %s, last_error = %s WHERE source_id = %s
            """, (status, error, source_id))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Update Status Failed: {e}")

    def check_analysis_exists(self, source_id):
        """Check if a record already has AI analysis data."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT 1 FROM intelligence WHERE source_id = %s AND summary IS NOT NULL LIMIT 1",
                (source_id,)
            )
            exists = cursor.fetchone() is not None
            conn.close()
            return exists
        except:
            return False

    def is_duplicate(self, new_url, new_content, new_summary=None) -> bool:
        """Checks for duplicate intelligence using URL and pg_trgm for content similarity."""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM intelligence WHERE url = %s LIMIT 1", (new_url,))
            if cursor.fetchone():
                logger.info(f"🚫 URL {new_url} 已存在，跳过。")
                conn.close()
                return True

            time_window = datetime.now() - timedelta(hours=settings.NEWS_DEDUPE_WINDOW_HOURS)
            new_text_for_sim = f"{new_content} {new_summary if new_summary else ''}"
            cursor.execute("""
                SELECT id, similarity(COALESCE(content, '') || ' ' || COALESCE(summary::text, ''), %s) AS sim_score
                FROM intelligence
                WHERE timestamp > %s
                AND (
                    similarity(COALESCE(content, ''), %s) > %s OR
                    similarity(COALESCE(summary::text, ''), %s) > %s OR
                    similarity(COALESCE(content, '') || ' ' || COALESCE(summary::text, ''), %s) > %s
                )
                ORDER BY sim_score DESC LIMIT 1
            """, (new_text_for_sim, time_window,
                  new_content, settings.NEWS_SIMILARITY_THRESHOLD,
                  new_summary if new_summary else '', settings.NEWS_SIMILARITY_THRESHOLD,
                  new_text_for_sim, settings.NEWS_SIMILARITY_THRESHOLD))
            result = cursor.fetchone()
            conn.close()
            if result:
                logger.info(f"🚫 发现语义重复情报 (ID: {result[0]}, 相似度: {result[1]:.2f})，跳过。")
                return True
            return False
        except Exception as e:
            logger.error(f"Duplicate Check Failed: {e}")
            return False

    # ── 事件聚类支持方法 ──────────────────────────────────────────────────

    def find_similar_pairs(self, source_ids: list, threshold: float = 0.45,
                           time_window_hours: int = 2) -> list:
        """
        在 source_ids 对应的记录中，用 pg_trgm 找出相似对。
        单次 DB 往返，O(n²) 仅在 DB 内执行。

        Returns:
            list of (source_id_a, source_id_b) tuples
        """
        if len(source_ids) < 2:
            return []
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT a.source_id, b.source_id
                FROM intelligence a
                JOIN intelligence b ON a.source_id < b.source_id
                WHERE a.source_id = ANY(%s)
                  AND b.source_id = ANY(%s)
                  AND ABS(EXTRACT(EPOCH FROM (a.timestamp - b.timestamp))) < %s
                  AND similarity(COALESCE(a.content,''), COALESCE(b.content,'')) > %s
            """, (source_ids, source_ids, time_window_hours * 3600, threshold))
            pairs = cursor.fetchall()
            conn.close()
            return [(r[0], r[1]) for r in pairs]
        except Exception as e:
            logger.error(f"find_similar_pairs 查询失败: {e}")
            return []

    def mark_clustered(self, source_ids: list, cluster_id: str, lead_source_id: str) -> None:
        """
        将非 lead 的同事件记录批量标记为 CLUSTERED。
          - is_cluster_lead = FALSE  （非 lead）
          - event_cluster_id = cluster_id
          - status = 'CLUSTERED'
        Lead 记录只写入 event_cluster_id，状态保持 PENDING。
        """
        if not source_ids:
            return
        follower_ids = [sid for sid in source_ids if sid != lead_source_id]
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            # 所有成员打上 cluster_id
            cursor.execute("""
                UPDATE intelligence
                SET event_cluster_id = %s
                WHERE source_id = ANY(%s)
            """, (cluster_id, source_ids))
            # Lead 标记
            cursor.execute("""
                UPDATE intelligence SET is_cluster_lead = TRUE
                WHERE source_id = %s
            """, (lead_source_id,))
            # Followers → CLUSTERED
            if follower_ids:
                cursor.execute("""
                    UPDATE intelligence
                    SET is_cluster_lead = FALSE,
                        status = 'CLUSTERED',
                        last_error = 'Suppressed: same event as ' || %s
                    WHERE source_id = ANY(%s)
                """, (lead_source_id, follower_ids))
            conn.commit()
            conn.close()
            logger.info(
                f"🔗 事件聚类 [{cluster_id[:8]}] | lead={lead_source_id[:20]} | "
                f"suppressed={len(follower_ids)} 条"
            )
        except Exception as e:
            logger.error(f"mark_clustered 失败: {e}")
