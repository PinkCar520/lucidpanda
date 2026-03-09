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
from src.alphasignal.utils.confidence import calc_confidence_score
from src.alphasignal.utils.entity_normalizer import normalize_entity_name
from src.alphasignal.utils.graph_reasoning import infer_event_chains, relation_signal


class IntelligenceRepo(DBBase):
    @staticmethod
    def _normalize_entities(entities):
        """规范化 LLM 实体输出，确保入库结构稳定。"""
        if not isinstance(entities, list):
            return []
        normalized = []
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            name = str(entity.get("name", "")).strip()
            if not name:
                continue
            normalized.append({
                "name": name,
                "type": str(entity.get("type", "unknown")).strip() or "unknown",
                "impact": str(entity.get("impact", "neutral")).strip() or "neutral",
            })
        return normalized

    @staticmethod
    def _normalize_relations(relations):
        """规范化 LLM 关系三元组输出。"""
        if not isinstance(relations, list):
            return []
        normalized = []
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            subject = str(relation.get("subject") or relation.get("from") or "").strip()
            predicate = str(relation.get("predicate") or relation.get("relation") or "").strip().lower()
            obj = str(relation.get("object") or relation.get("to") or "").strip()
            if not subject or not predicate or not obj:
                continue
            direction = str(relation.get("direction", "forward")).strip().lower()
            if direction in {"both", "two_way"}:
                direction = "bidirectional"
            elif direction in {"positive", "negative"}:
                direction = "forward"
            if direction not in {"forward", "bidirectional"}:
                direction = "forward"
            try:
                strength = float(relation.get("strength", 0.5))
            except Exception:
                strength = 0.5
            strength = max(0.0, min(1.0, strength))
            normalized.append({
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "direction": direction,
                "strength": strength,
            })
        return normalized

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
            oil = raw_data.get('oil_price_snapshot')
            if oil is None: oil = self.get_market_snapshot("CL=F", news_time)

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
                    dxy_snapshot, us10y_snapshot, gvz_snapshot, gold_price_snapshot, oil_price_snapshot,
                    fed_regime, embedding, source_name
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (source_id) DO NOTHING
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
                float(oil) if oil is not None else None,
                float(raw_data.get('fed_val', 0.0)),
                embedding_binary,
                raw_data.get('source'),
            ))
            row = cursor.fetchone()
            if not row:
                # If DO NOTHING triggered, fetch the existing ID
                cursor.execute("SELECT id FROM intelligence WHERE source_id = %s", (raw_data.get('id'),))
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
            entities = self._normalize_entities(analysis_result.get('entities'))
            relation_triples = self._normalize_relations(analysis_result.get('relations'))

            cursor.execute("""
                UPDATE intelligence SET
                    summary = %s, sentiment = %s, urgency_score = %s,
                    market_implication = %s, actionable_advice = %s,
                    sentiment_score = %s, macro_adjustment = %s,
                    entities = %s,
                    relation_triples = %s,
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
                to_jsonb(entities),
                to_jsonb(relation_triples),
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
        corroboration_count = len(source_ids)
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            # 所有成员打上 cluster_id
            cursor.execute("""
                UPDATE intelligence
                SET event_cluster_id = %s,
                    corroboration_count = %s
                WHERE source_id = ANY(%s)
            """, (cluster_id, corroboration_count, source_ids))
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

    # ── 事件知识图谱 ──────────────────────────────────────────────────────

    def _upsert_entity_node(self, cursor, entity_name: str, entity_type: str = "unknown") -> int:
        canonical_name = normalize_entity_name(entity_name)
        normalized_name = canonical_name.strip().lower()
        cursor.execute("""
            INSERT INTO entity_nodes (entity_name, normalized_name, entity_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (normalized_name, entity_type)
            DO UPDATE SET entity_name = EXCLUDED.entity_name
            RETURNING node_id
        """, (canonical_name.strip(), normalized_name, entity_type or "unknown"))
        return cursor.fetchone()[0]

    def _upsert_graph_edge(
        self,
        cursor,
        from_node_id: int,
        to_node_id: int,
        relation: str,
        direction: str,
        strength: float,
        confidence_score: float,
        cluster_id: str,
        source_id: str,
        intelligence_id: int,
        metadata: dict | None = None,
    ) -> None:
        cursor.execute("""
            INSERT INTO entity_edges (
                from_node_id, to_node_id, relation, direction,
                strength, confidence_score, event_cluster_id,
                evidence_source_id, intelligence_id, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (from_node_id, to_node_id, relation, event_cluster_id, evidence_source_id)
            DO UPDATE SET
                strength = GREATEST(entity_edges.strength, EXCLUDED.strength),
                confidence_score = GREATEST(entity_edges.confidence_score, EXCLUDED.confidence_score),
                metadata = COALESCE(entity_edges.metadata, '{}'::jsonb) || EXCLUDED.metadata
        """, (
            from_node_id,
            to_node_id,
            relation,
            direction,
            strength,
            confidence_score,
            cluster_id,
            source_id,
            intelligence_id,
            Json(metadata or {}),
        ))

    def _get_intelligence_context(self, cursor, source_id: str) -> dict | None:
        cursor.execute("""
            SELECT id, source_id, event_cluster_id, urgency_score, source_credibility_score, timestamp
            FROM intelligence
            WHERE source_id = %s
            LIMIT 1
        """, (source_id,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "source_id": row[1],
            "event_cluster_id": row[2],
            "urgency_score": row[3],
            "source_credibility_score": row[4],
            "timestamp": row[5],
        }

    def _upsert_cross_asset_edges(
        self,
        cursor,
        source_id: str,
        context: dict,
        sentiment_score: float | None,
    ) -> None:
        """
        在每条情报图谱中补充跨资产传播边：
        DXY / US10Y / Oil -> Gold
        DXY <-> US10Y / Oil -> US10Y
        """
        if not context:
            return
        cluster_id = context.get("event_cluster_id") or f"single:{source_id}"
        intelligence_id = context.get("id")
        confidence_score = calc_confidence_score(
            corroboration_count=1,
            source_credibility_score=context.get("source_credibility_score"),
            urgency_score=context.get("urgency_score"),
            timestamp=context.get("timestamp"),
        )
        base_strength = 0.55
        signal = float(sentiment_score or 0.0)

        gold_id = self._upsert_entity_node(cursor, "Gold", "asset")
        dxy_id = self._upsert_entity_node(cursor, "DXY", "asset")
        tnx_id = self._upsert_entity_node(cursor, "US10Y", "asset")
        oil_id = self._upsert_entity_node(cursor, "Oil", "asset")

        if signal < -0.1:
            dxy_relation = "usd_strength"
            tnx_relation = "real_yield_up"
        elif signal > 0.1:
            dxy_relation = "usd_weakness"
            tnx_relation = "yield_down"
        else:
            dxy_relation = "macro_coupling"
            tnx_relation = "macro_coupling"

        oil_relation = "inflation_up" if signal >= 0 else "risk_off"

        self._upsert_graph_edge(
            cursor, dxy_id, gold_id, dxy_relation, "forward",
            base_strength, confidence_score, cluster_id, source_id, intelligence_id,
            {"source": "cross_asset_heuristic", "asset": "DXY"}
        )
        self._upsert_graph_edge(
            cursor, tnx_id, gold_id, tnx_relation, "forward",
            base_strength, confidence_score, cluster_id, source_id, intelligence_id,
            {"source": "cross_asset_heuristic", "asset": "US10Y"}
        )
        self._upsert_graph_edge(
            cursor, oil_id, gold_id, oil_relation, "forward",
            0.5, confidence_score, cluster_id, source_id, intelligence_id,
            {"source": "cross_asset_heuristic", "asset": "Oil"}
        )
        self._upsert_graph_edge(
            cursor, dxy_id, tnx_id, "macro_coupling", "bidirectional",
            0.45, confidence_score, cluster_id, source_id, intelligence_id,
            {"source": "cross_asset_heuristic"}
        )
        self._upsert_graph_edge(
            cursor, tnx_id, dxy_id, "macro_coupling", "bidirectional",
            0.45, confidence_score, cluster_id, source_id, intelligence_id,
            {"source": "cross_asset_heuristic", "reverse": True}
        )
        self._upsert_graph_edge(
            cursor, oil_id, tnx_id, "inflation_coupling", "forward",
            0.4, confidence_score, cluster_id, source_id, intelligence_id,
            {"source": "cross_asset_heuristic"}
        )

    def upsert_knowledge_graph(self, source_id: str, analysis_result: dict) -> None:
        """
        将单条情报的实体和关系写入图谱（节点/边）。
        调用时机：update_intelligence_analysis 成功后。
        """
        if not source_id:
            return

        entities = self._normalize_entities((analysis_result or {}).get("entities"))
        relations = self._normalize_relations((analysis_result or {}).get("relations"))
        if not entities and not relations:
            return

        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            context = self._get_intelligence_context(cursor, source_id)
            if not context:
                conn.close()
                return

            cluster_id = context.get("event_cluster_id") or f"single:{source_id}"
            confidence_score = calc_confidence_score(
                corroboration_count=1,
                source_credibility_score=context.get("source_credibility_score"),
                urgency_score=context.get("urgency_score"),
                timestamp=context.get("timestamp"),
            )
            sentiment_score = analysis_result.get("sentiment_score")

            node_ids: dict[tuple[str, str], int] = {}
            for entity in entities:
                entity_name = entity["name"]
                entity_type = entity.get("type", "unknown")
                node_id = self._upsert_entity_node(cursor, entity_name, entity_type)
                node_ids[(entity_name.strip().lower(), entity_type.strip().lower())] = node_id

            for relation in relations:
                sub_name = relation["subject"]
                obj_name = relation["object"]
                sub_type = "unknown"
                obj_type = "unknown"
                sub_key = (sub_name.strip().lower(), sub_type)
                obj_key = (obj_name.strip().lower(), obj_type)

                if sub_key not in node_ids:
                    node_ids[sub_key] = self._upsert_entity_node(cursor, sub_name, sub_type)
                if obj_key not in node_ids:
                    node_ids[obj_key] = self._upsert_entity_node(cursor, obj_name, obj_type)

                metadata = {"source_id": source_id, "predicate": relation["predicate"], "source": "llm_relation_extract"}
                self._upsert_graph_edge(
                    cursor,
                    node_ids[sub_key],
                    node_ids[obj_key],
                    relation["predicate"],
                    relation["direction"],
                    relation["strength"],
                    confidence_score,
                    cluster_id,
                    source_id,
                    context.get("id"),
                    metadata,
                )

                if relation["direction"] == "bidirectional":
                    self._upsert_graph_edge(
                        cursor,
                        node_ids[obj_key],
                        node_ids[sub_key],
                        relation["predicate"],
                        relation["direction"],
                        relation["strength"],
                        confidence_score,
                        cluster_id,
                        source_id,
                        context.get("id"),
                        {**metadata, "reverse": True},
                    )

            self._upsert_cross_asset_edges(cursor, source_id, context, sentiment_score)

            conn.commit()
            conn.close()
            logger.info(f"🕸️ 图谱写入完成: source_id={source_id}, entities={len(entities)}, relations={len(relations)}")
        except Exception as e:
            logger.error(f"图谱写入失败 [{source_id}]: {e}")

    def refresh_relation_rule_stats(self, limit: int = 5000) -> None:
        """
        基于历史 outcome 对关系规则做简单学习，更新 relation_rule_stats.weight。
        """
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT relation_triples, gold_price_snapshot, price_1h
                FROM intelligence
                WHERE status = 'COMPLETED'
                  AND relation_triples IS NOT NULL
                  AND gold_price_snapshot IS NOT NULL
                  AND price_1h IS NOT NULL
                ORDER BY timestamp DESC
                LIMIT %s
            """, (max(100, limit),))
            rows = cursor.fetchall()

            stats: dict[str, dict[str, int]] = {}
            for row in rows:
                relation_triples = row["relation_triples"]
                entry = float(row["gold_price_snapshot"])
                exit_price = float(row["price_1h"])
                price_up = exit_price > entry
                price_down = exit_price < entry

                triples = self._normalize_relations(relation_triples)
                for triple in triples:
                    relation = triple["predicate"].strip().lower()
                    signal = relation_signal(relation)
                    if signal == "NEUTRAL":
                        continue
                    agg = stats.setdefault(relation, {
                        "bullish_hits": 0,
                        "bullish_total": 0,
                        "bearish_hits": 0,
                        "bearish_total": 0,
                    })
                    if signal == "BULLISH_GOLD":
                        agg["bullish_total"] += 1
                        if price_up:
                            agg["bullish_hits"] += 1
                    elif signal == "BEARISH_GOLD":
                        agg["bearish_total"] += 1
                        if price_down:
                            agg["bearish_hits"] += 1

            for relation, agg in stats.items():
                total = agg["bullish_total"] + agg["bearish_total"]
                hits = agg["bullish_hits"] + agg["bearish_hits"]
                if total <= 0:
                    continue
                hit_rate = hits / total
                weight = max(0.6, min(1.25, 0.75 + hit_rate * 0.7))
                cursor.execute("""
                    INSERT INTO relation_rule_stats (
                        relation, bullish_hits, bullish_total,
                        bearish_hits, bearish_total, hit_rate, weight, last_updated
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    ON CONFLICT (relation)
                    DO UPDATE SET
                        bullish_hits = EXCLUDED.bullish_hits,
                        bullish_total = EXCLUDED.bullish_total,
                        bearish_hits = EXCLUDED.bearish_hits,
                        bearish_total = EXCLUDED.bearish_total,
                        hit_rate = EXCLUDED.hit_rate,
                        weight = EXCLUDED.weight,
                        last_updated = NOW()
                """, (
                    relation,
                    agg["bullish_hits"],
                    agg["bullish_total"],
                    agg["bearish_hits"],
                    agg["bearish_total"],
                    round(hit_rate, 4),
                    round(weight, 4),
                ))

            conn.commit()
            conn.close()
            if stats:
                logger.info(f"📚 关系规则学习更新完成: {len(stats)} 条 relation 权重")
        except Exception as e:
            logger.error(f"refresh_relation_rule_stats 失败: {e}")

    def get_relation_rule_weights(self, relations: list[str]) -> dict[str, float]:
        if not relations:
            return {}
        normalized = sorted({str(r).strip().lower() for r in relations if str(r).strip()})
        if not normalized:
            return {}
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT relation, weight
                FROM relation_rule_stats
                WHERE relation = ANY(%s)
            """, (normalized,))
            rows = cursor.fetchall()
            conn.close()
            return {row["relation"]: float(row["weight"]) for row in rows}
        except Exception as e:
            logger.error(f"get_relation_rule_weights 失败: {e}")
            return {}

    def get_event_graph(self, event_cluster_id: str) -> dict:
        """按 event_cluster_id 获取图谱节点、边与可解释推理链。"""
        if not event_cluster_id:
            return {"nodes": [], "edges": [], "inferences": [], "evidence": []}
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)

            cursor.execute("""
                SELECT DISTINCT
                    n.node_id, n.entity_name, n.entity_type
                FROM entity_nodes n
                JOIN entity_edges e
                  ON n.node_id = e.from_node_id OR n.node_id = e.to_node_id
                WHERE e.event_cluster_id = %s
                ORDER BY n.entity_name
            """, (event_cluster_id,))
            nodes = [dict(row) for row in cursor.fetchall()]

            cursor.execute("""
                SELECT
                    e.edge_id,
                    e.relation,
                    e.direction,
                    e.strength,
                    e.confidence_score,
                    e.created_at,
                    e.evidence_source_id,
                    e.intelligence_id,
                    fn.node_id AS from_node_id,
                    fn.entity_name AS from_entity,
                    fn.entity_type AS from_type,
                    tn.node_id AS to_node_id,
                    tn.entity_name AS to_entity,
                    tn.entity_type AS to_type
                FROM entity_edges e
                JOIN entity_nodes fn ON e.from_node_id = fn.node_id
                JOIN entity_nodes tn ON e.to_node_id = tn.node_id
                WHERE e.event_cluster_id = %s
                ORDER BY e.confidence_score DESC, e.strength DESC, e.edge_id DESC
                LIMIT 300
            """, (event_cluster_id,))
            edges = [dict(row) for row in cursor.fetchall()]
            relation_weights = self.get_relation_rule_weights([edge.get("relation") for edge in edges])

            cursor.execute("""
                SELECT id, source_id, timestamp, summary
                FROM intelligence
                WHERE event_cluster_id = %s
                  AND status = 'COMPLETED'
                ORDER BY timestamp DESC
                LIMIT 20
            """, (event_cluster_id,))
            evidence = [dict(row) for row in cursor.fetchall()]

            conn.close()
            return {
                "nodes": nodes,
                "edges": edges,
                "inferences": infer_event_chains(edges, relation_weights=relation_weights),
                "evidence": evidence,
                "relation_weights": relation_weights,
            }
        except Exception as e:
            logger.error(f"get_event_graph 失败 [{event_cluster_id}]: {e}")
            return {"nodes": [], "edges": [], "inferences": [], "evidence": [], "relation_weights": {}}

    def get_entity_graph(self, entity_name: str, limit: int = 100) -> dict:
        """按实体名称返回邻接子图。"""
        if not entity_name:
            return {"center": None, "nodes": [], "edges": []}
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT node_id, entity_name, entity_type
                FROM entity_nodes
                WHERE normalized_name = %s
                LIMIT 1
            """, (entity_name.strip().lower(),))
            center = cursor.fetchone()
            if not center:
                conn.close()
                return {"center": None, "nodes": [], "edges": []}

            center_id = center["node_id"]
            cursor.execute("""
                SELECT
                    e.edge_id,
                    e.relation,
                    e.direction,
                    e.strength,
                    e.confidence_score,
                    e.event_cluster_id,
                    fn.node_id AS from_node_id,
                    fn.entity_name AS from_entity,
                    fn.entity_type AS from_type,
                    tn.node_id AS to_node_id,
                    tn.entity_name AS to_entity,
                    tn.entity_type AS to_type
                FROM entity_edges e
                JOIN entity_nodes fn ON e.from_node_id = fn.node_id
                JOIN entity_nodes tn ON e.to_node_id = tn.node_id
                WHERE e.from_node_id = %s OR e.to_node_id = %s
                ORDER BY e.confidence_score DESC, e.strength DESC
                LIMIT %s
            """, (center_id, center_id, max(1, limit)))
            edges = [dict(row) for row in cursor.fetchall()]

            node_map = {center_id: dict(center)}
            for edge in edges:
                node_map[edge["from_node_id"]] = {
                    "node_id": edge["from_node_id"],
                    "entity_name": edge["from_entity"],
                    "entity_type": edge["from_type"],
                }
                node_map[edge["to_node_id"]] = {
                    "node_id": edge["to_node_id"],
                    "entity_name": edge["to_entity"],
                    "entity_type": edge["to_type"],
                }

            conn.close()
            return {"center": dict(center), "nodes": list(node_map.values()), "edges": edges}
        except Exception as e:
            logger.error(f"get_entity_graph 失败 [{entity_name}]: {e}")
            return {"center": None, "nodes": [], "edges": []}

    def find_graph_path(
        self,
        from_entity: str,
        to_entity: str,
        max_hops: int = 2,
        min_confidence: float = 0.0,
        relation: str | None = None,
        event_cluster_id: str | None = None,
    ) -> dict:
        """搜索 from_entity 到 to_entity 的 1-hop / 2-hop 路径。"""
        if not from_entity or not to_entity:
            return {"paths": [], "max_hops": max_hops}

        from_norm = from_entity.strip().lower()
        to_norm = to_entity.strip().lower()
        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            sql = """
                SELECT
                    e.edge_id,
                    e.relation,
                    e.direction,
                    e.strength,
                    e.confidence_score,
                    e.event_cluster_id,
                    e.created_at,
                    e.evidence_source_id,
                    e.intelligence_id,
                    fn.entity_name AS from_entity,
                    tn.entity_name AS to_entity
                FROM entity_edges e
                JOIN entity_nodes fn ON e.from_node_id = fn.node_id
                JOIN entity_nodes tn ON e.to_node_id = tn.node_id
                WHERE e.confidence_score >= %s
            """
            params = [max(0.0, float(min_confidence or 0.0))]
            if relation:
                sql += " AND e.relation = %s"
                params.append(relation.strip().lower())
            if event_cluster_id:
                sql += " AND e.event_cluster_id = %s"
                params.append(event_cluster_id)
            sql += " ORDER BY e.confidence_score DESC, e.strength DESC LIMIT 2000"
            cursor.execute(sql, tuple(params))
            edges = [dict(row) for row in cursor.fetchall()]
            conn.close()

            paths = []
            for edge in edges:
                if edge["from_entity"].strip().lower() == from_norm and edge["to_entity"].strip().lower() == to_norm:
                    paths.append({
                        "hops": 1,
                        "edges": [edge],
                        "score": round(float(edge.get("confidence_score") or 50.0), 1),
                    })

            if max_hops >= 2:
                first_hop = [e for e in edges if e["from_entity"].strip().lower() == from_norm]
                second_hop = [e for e in edges if e["to_entity"].strip().lower() == to_norm]
                for e1 in first_hop:
                    for e2 in second_hop:
                        if e1["to_entity"].strip().lower() != e2["from_entity"].strip().lower():
                            continue
                        score = round(
                            (float(e1.get("confidence_score") or 50.0) + float(e2.get("confidence_score") or 50.0)) / 2.0,
                            1
                        )
                        paths.append({"hops": 2, "edges": [e1, e2], "score": score})

            paths = sorted(paths, key=lambda x: x["score"], reverse=True)[:10]
            return {
                "paths": paths,
                "max_hops": max_hops,
                "min_confidence": min_confidence,
                "relation": relation,
                "event_cluster_id": event_cluster_id,
            }
        except Exception as e:
            logger.error(f"find_graph_path 失败 [{from_entity} -> {to_entity}]: {e}")
            return {"paths": [], "max_hops": max_hops, "min_confidence": min_confidence}

    # ── 事件知识图谱（Phase 2.2）──────────────────────────────────────────

    def _upsert_entity_node(self, cursor, name: str, entity_type: str = "unknown") -> int | None:
        clean_name = (name or "").strip()
        clean_type = (entity_type or "unknown").strip().lower() or "unknown"
        if not clean_name:
            return None
        canonical_name = normalize_entity_name(clean_name)
        normalized_name = canonical_name.lower()
        cursor.execute("""
            INSERT INTO entity_nodes (entity_name, normalized_name, entity_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (normalized_name, entity_type) DO UPDATE
                SET entity_name = EXCLUDED.entity_name
            RETURNING node_id
        """, (canonical_name, normalized_name, clean_type))
        row = cursor.fetchone()
        return row[0] if row else None

    def ingest_knowledge_graph(self, source_id: str, analysis_result: dict) -> bool:
        """
        将单条情报的实体与关系写入图谱。
        调用时机：update_intelligence_analysis 之后。
        """
        entities = self._normalize_entities((analysis_result or {}).get("entities"))
        relations = self._normalize_relations((analysis_result or {}).get("relations"))
        if not entities and not relations:
            return False

        try:
            conn = self._get_conn()
            cursor = conn.cursor(cursor_factory=DictCursor)
            cursor.execute("""
                SELECT id, event_cluster_id, urgency_score, source_credibility_score, timestamp
                FROM intelligence
                WHERE source_id = %s
                LIMIT 1
            """, (source_id,))
            row = cursor.fetchone()
            if not row:
                conn.close()
                return False

            intelligence_id = row["id"]
            cluster_id = row["event_cluster_id"] or f"single:{source_id}"
            urgency_score = row["urgency_score"]
            source_credibility_score = row["source_credibility_score"]
            intel_timestamp = row["timestamp"]
            edge_confidence = calc_confidence_score(
                corroboration_count=1,
                source_credibility_score=source_credibility_score,
                urgency_score=urgency_score,
                timestamp=intel_timestamp,
            )

            node_map: dict[tuple[str, str], int] = {}
            for entity in entities:
                node_id = self._upsert_entity_node(
                    cursor,
                    entity.get("name"),
                    entity.get("type", "unknown"),
                )
                if node_id:
                    node_map[(entity["name"].strip().lower(), entity["type"].strip().lower())] = node_id

            for rel in relations:
                subj = rel["subject"].strip()
                obj = rel["object"].strip()
                subj_key = (subj.lower(), "unknown")
                obj_key = (obj.lower(), "unknown")

                from_node_id = node_map.get(subj_key) or self._upsert_entity_node(cursor, subj, "unknown")
                to_node_id = node_map.get(obj_key) or self._upsert_entity_node(cursor, obj, "unknown")
                if not from_node_id or not to_node_id:
                    continue
                node_map[subj_key] = from_node_id
                node_map[obj_key] = to_node_id

                cursor.execute("""
                    INSERT INTO entity_edges (
                        from_node_id, to_node_id, relation, direction, strength,
                        confidence_score, event_cluster_id, evidence_source_id, intelligence_id, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (from_node_id, to_node_id, relation, event_cluster_id, evidence_source_id)
                    DO UPDATE SET
                        strength = GREATEST(entity_edges.strength, EXCLUDED.strength),
                        confidence_score = GREATEST(entity_edges.confidence_score, EXCLUDED.confidence_score),
                        metadata = EXCLUDED.metadata
                """, (
                    from_node_id,
                    to_node_id,
                    rel["predicate"],
                    rel["direction"],
                    rel["strength"],
                    edge_confidence,
                    cluster_id,
                    source_id,
                    intelligence_id,
                    Json({"source": "llm_relation_extract"}),
                ))
                if rel["direction"] == "bidirectional":
                    cursor.execute("""
                        INSERT INTO entity_edges (
                            from_node_id, to_node_id, relation, direction, strength,
                            confidence_score, event_cluster_id, evidence_source_id, intelligence_id, metadata
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (from_node_id, to_node_id, relation, event_cluster_id, evidence_source_id)
                        DO UPDATE SET
                            strength = GREATEST(entity_edges.strength, EXCLUDED.strength),
                            confidence_score = GREATEST(entity_edges.confidence_score, EXCLUDED.confidence_score),
                            metadata = EXCLUDED.metadata
                    """, (
                        to_node_id,
                        from_node_id,
                        rel["predicate"],
                        rel["direction"],
                        rel["strength"],
                        edge_confidence,
                        cluster_id,
                        source_id,
                        intelligence_id,
                        Json({"source": "llm_relation_extract", "reverse": True}),
                    ))

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"ingest_knowledge_graph 失败 [{source_id}]: {e}")
            return False
