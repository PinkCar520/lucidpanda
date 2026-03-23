"""
db/intelligence.py — 情报域
============================
情报 CRUD、去重（URL/pg_trgm/pgvector）、向量嵌入、信源可信度。
"""
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import pytz
import psycopg
from psycopg.types.json import Jsonb
from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger
from src.lucidpanda.db.base import DBBase
from src.lucidpanda.utils.confidence import calc_confidence_score
from src.lucidpanda.utils.entity_normalizer import normalize_entity_name, normalize_entity_type
from src.lucidpanda.utils.graph_reasoning import infer_event_chains, relation_signal


class IntelligenceRepo(DBBase):
    @staticmethod
    def _parse_float(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if not isinstance(value, str):
            return None
        cleaned = (
            value.replace("%", "")
            .replace("$", "")
            .replace("K", "")
            .replace("M", "")
            .replace(",", "")
            .strip()
        )
        try:
            return float(cleaned)
        except Exception:
            return None

    def _compute_macro_surprise_std(self, event_code: str, lookback_years: int = 3):
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT actual_value, forecast_value
                        FROM macro_event
                        WHERE event_code = %s
                          AND actual_value IS NOT NULL
                          AND forecast_value IS NOT NULL
                          AND release_date >= (CURRENT_DATE - (%s || ' years')::interval)
                    """, (event_code, lookback_years))
                    rows = cursor.fetchall()
            surprises = []
            for row in rows:
                actual = self._parse_float(row["actual_value"])
                forecast = self._parse_float(row["forecast_value"])
                if actual is None or forecast is None:
                    continue
                surprises.append(actual - forecast)
            if len(surprises) < 2:
                return None
            import numpy as _np
            return float(_np.std(_np.array(surprises), ddof=1))
        except Exception as e:
            logger.warning(f"⚠️ 计算宏观 surprise std 失败: {e}")
            return None

    def _extract_macro_event_from_trace(self, agent_trace):
        if not isinstance(agent_trace, dict):
            return None
        tool_results = agent_trace.get("tool_results") or []
        if not isinstance(tool_results, list):
            return None
        for tool in tool_results:
            if not isinstance(tool, dict):
                continue
            if tool.get("name") != "query_macro_expectation":
                continue
            result = tool.get("result") or {}
            best = result.get("best_match") or {}
            event_code = best.get("event_code")
            parsed = best.get("parsed") or {}
            actual = parsed.get("actual")
            forecast = parsed.get("forecast")
            if event_code and actual is not None and forecast is not None:
                return {
                    "event_code": event_code,
                    "actual": actual,
                    "forecast": forecast,
                }
        return None

    def compute_expectation_gap(self, agent_trace):
        info = self._extract_macro_event_from_trace(agent_trace)
        if not info:
            return None
        std = self._compute_macro_surprise_std(info["event_code"])
        if std is None or std == 0:
            return None
        try:
            return (float(info["actual"]) - float(info["forecast"])) / float(std)
        except Exception:
            return None

    def update_expectation_gap(self, source_id: str, expectation_gap: float) -> None:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE intelligence
                        SET expectation_gap = %s
                        WHERE source_id = %s
                    """, (float(expectation_gap), source_id))
                    conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ expectation_gap 更新失败 [{source_id}]: {e}")

    def backfill_expectation_gap(self, limit: int = 500) -> int:
        updated = 0
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT source_id, agent_trace
                        FROM intelligence
                        WHERE expectation_gap IS NULL
                          AND agent_trace IS NOT NULL
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (limit,))
                    rows = cursor.fetchall()
            for row in rows:
                gap = self.compute_expectation_gap(row["agent_trace"])
                if gap is None:
                    continue
                self.update_expectation_gap(row["source_id"], gap)
                updated += 1
        except Exception as e:
            logger.warning(f"⚠️ expectation_gap 回填失败: {e}")
        return updated

    def compute_alpha_return_for_record(self, record_id: int, window: int = 200):
        """
        近似 Alpha：用 gold_return 回归 dxy/us10y 水平，取残差。
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    # 1. Fetch the target record's data
                    cursor.execute("""
                        SELECT id, gold_price_snapshot, price_1h, dxy_snapshot, us10y_snapshot, timestamp
                        FROM intelligence
                        WHERE id = %s
                          AND gold_price_snapshot IS NOT NULL
                          AND price_1h IS NOT NULL
                          AND dxy_snapshot IS NOT NULL
                          AND us10y_snapshot IS NOT NULL
                    """, (record_id,))
                    target_row = cursor.fetchone()
                    if not target_row:
                        return None

                    # Ensure gold_price_snapshot is not zero before division
                    if float(target_row["gold_price_snapshot"]) == 0:
                        return None

                    target_gold_ret = (float(target_row["price_1h"]) - float(target_row["gold_price_snapshot"])) / float(target_row["gold_price_snapshot"])
                    target_dxy = float(target_row["dxy_snapshot"])
                    target_us10y = float(target_row["us10y_snapshot"])
                    target_timestamp = target_row["timestamp"]


                    # 2. Fetch historical data for regression, older than the target record
                    cursor.execute("""
                        SELECT gold_price_snapshot, price_1h, dxy_snapshot, us10y_snapshot
                        FROM intelligence
                        WHERE gold_price_snapshot IS NOT NULL
                          AND price_1h IS NOT NULL
                          AND dxy_snapshot IS NOT NULL
                          AND us10y_snapshot IS NOT NULL
                          AND timestamp < %s -- Key change: historical data before target
                          AND id != %s -- Exclude the target record itself from the historical window
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (target_timestamp, record_id, window))
                    historical_rows = cursor.fetchall()

            if len(historical_rows) < 3: # Need at least 3 points for regression
                logger.warning(f"⚠️ alpha_return 计算失败 [ID:{record_id}]: 历史回归数据不足 {len(historical_rows)} 条")
                return None

            import numpy as _np
            import statsmodels.api as _sm

            y_data = []
            X_dxy_data = []
            X_us10y_data = []

            for row in historical_rows:
                entry = float(row["gold_price_snapshot"])
                exit_price = float(row["price_1h"])
                if entry == 0: # Avoid division by zero
                    continue
                gold_ret = (exit_price - entry) / entry
                y_data.append(gold_ret)
                X_dxy_data.append(float(row["dxy_snapshot"]))
                X_us10y_data.append(float(row["us10y_snapshot"]))

            if len(y_data) < 3: # After filtering, still need at least 3 points
                logger.warning(f"⚠️ alpha_return 计算失败 [ID:{record_id}]: 过滤后历史回归数据不足 {len(y_data)} 条")
                return None

            y = _np.array(y_data, dtype=float)
            X = _np.column_stack([
                _np.array(X_dxy_data, dtype=float),
                _np.array(X_us10y_data, dtype=float),
            ])
            X = _np.column_stack([_np.ones(len(X)), X]) # Add intercept

            model = _sm.OLS(y, X).fit()

            # 5. Predict alpha for the target record
            pred = model.predict([1.0, target_dxy, target_us10y])[0]
            alpha_return = float(target_gold_ret - pred)
            return alpha_return
        except Exception as e:
            logger.warning(f"⚠️ alpha_return 计算失败 [ID:{record_id}]: {e}")
            return None

    def update_alpha_return(self, record_id: int, alpha_return: float) -> None:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE intelligence
                        SET alpha_return = %s
                        WHERE id = %s
                    """, (float(alpha_return), record_id))
                    conn.commit()
        except Exception as e:
            logger.warning(f"⚠️ alpha_return 更新失败 [{record_id}]: {e}")

    def backfill_alpha_return(self, limit: int = 500, window: int = 200) -> int:
        updated = 0
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT id
                        FROM intelligence
                        WHERE alpha_return IS NULL
                          AND gold_price_snapshot IS NOT NULL
                          AND price_1h IS NOT NULL
                          AND dxy_snapshot IS NOT NULL
                          AND us10y_snapshot IS NOT NULL
                        ORDER BY timestamp DESC
                        LIMIT %s
                    """, (limit,))
                    rows = cursor.fetchall()
            for row in rows:
                alpha = self.compute_alpha_return_for_record(row["id"], window=window)
                if alpha is None:
                    continue
                self.update_alpha_return(row["id"], alpha)
                updated += 1
        except Exception as e:
            logger.warning(f"⚠️ alpha_return 回填失败: {e}")
        return updated
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

    def is_semantic_duplicate(self, vector, threshold: float = 0.85) -> dict:
        """
        查询 pgvector 判断语义重复 (HNSW 优化)。
        返回dict: {status: 'NEW'|'DUP'|'SUSPECTED', sim: float, lead_id: int, lead_summary: str}
        """
        try:
            vec_list = vector.tolist() if hasattr(vector, 'tolist') else list(vector)
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    # HNSW 召回最近的一条记录
                    cursor.execute("""
                        SELECT source_id, summary::text, 1 - (embedding_vec <=> %s::vector) AS sim
                        FROM intelligence
                        WHERE embedding_vec IS NOT NULL
                          AND timestamp > NOW() - INTERVAL '48 hours'
                        ORDER BY embedding_vec <=> %s::vector
                        LIMIT 1
                    """, (vec_list, vec_list))
                    row = cursor.fetchone()
                    
                    if not row:
                        return {"status": "NEW", "sim": 0.0}
                    
                    sim = row['sim']
                    # 确定性重复阈值 (e.g. 0.95)
                    if sim > 0.95:
                        return {"status": "DUP", "sim": sim, "lead_id": row['source_id']}
                    
                    # 疑似重复阈值 (待 Delta 判定)
                    if sim > 0.65:
                        return {
                            "status": "SUSPECTED", 
                            "sim": sim, 
                            "lead_id": row['source_id'], 
                            "lead_summary": row['summary']
                        }
                    
            return {"status": "NEW", "sim": sim if 'sim' in locals() else 0.0}
        except Exception as e:
            logger.warning(f"⚠️ pgvector HNSW 语义查询失败: {e}")
            return {"status": "ERROR", "error": str(e)}

    def save_embedding_vec(self, source_id: str, vector) -> None:
        """将 BERT 嵌入向量持久化到 intelligence 表的 embedding_vec 列。"""
        try:
            vec_list = vector.tolist() if hasattr(vector, 'tolist') else list(vector)
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE intelligence
                        SET embedding_vec = %s::vector
                        WHERE source_id = %s
                    """, (vec_list, source_id))
                    conn.commit()
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
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
        except Exception as e:
            logger.error(f"Update Outcome Failed: {e}")

    def get_pending_outcomes(self):
        """Get records older than 1 hour that lack any of the outcome prices."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM intelligence
                        WHERE (price_1h IS NULL OR price_15m IS NULL OR price_4h IS NULL OR price_12h IS NULL)
                        AND timestamp < NOW() - INTERVAL '1 hour'
                        ORDER BY timestamp DESC LIMIT 50
                    """)
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Pending Outcomes Failed: {e}")
            return []

    # ── 情报写入 ──────────────────────────────────────────────────────────

    def save_raw_intelligence(self, raw_data, market_snapshots=None, conn=None):
        """
        Save raw intelligence data immediately (before analysis).
        
        Args:
            raw_data: The raw item data.
            market_snapshots: Optional dict of pre-fetched market snapshots.
            conn: Optional existing DB connection to reuse.
        """
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

            # Use pre-fetched snapshots if available, otherwise fetch (cached)
            snaps = market_snapshots or {}
            
            dxy = raw_data.get('dxy_snapshot') or snaps.get("DX-Y.NYB")
            if dxy is None: dxy = self.get_market_snapshot("DX-Y.NYB", news_time)
            
            us10y = raw_data.get('us10y_snapshot') or snaps.get("^TNX")
            if us10y is None: us10y = self.get_market_snapshot("^TNX", news_time)
            
            gvz = raw_data.get('gvz_snapshot') or snaps.get("^GVZ")
            if gvz is None: gvz = self.get_market_snapshot("^GVZ", news_time)
            
            gold = raw_data.get('gold_price_snapshot') or snaps.get("GC=F")
            if gold is None: gold = self.get_market_snapshot("GC=F", news_time)
            
            oil = raw_data.get('oil_price_snapshot') or snaps.get("CL=F")
            if oil is None: oil = self.get_market_snapshot("CL=F", news_time)

            # Define the actual save logic
            def _execute_save(active_conn):
                with active_conn.cursor() as cursor:

                    embedding_binary = None
                    if 'embedding' in raw_data and raw_data['embedding'] is not None:
                        import pickle
                        embedding_binary = pickle.dumps(raw_data['embedding'])

                    cursor.execute("""
                        INSERT INTO intelligence (
                            source_id, author, content, url, timestamp,
                            market_session, clustering_score, exhaustion_score,
                            dxy_snapshot, us10y_snapshot, gvz_snapshot, gold_price_snapshot, oil_price_snapshot,
                            fed_regime, embedding, source_name, category
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
                        raw_data.get('category', 'macro_gold'),
                    ))
                    row = cursor.fetchone()
                    if not row:
                        cursor.execute("SELECT id FROM intelligence WHERE source_id = %s", (raw_data.get('id'),))
                        row = cursor.fetchone()
                    active_conn.commit()
                    return row['id'] if row else None

            if conn:
                return _execute_save(conn)
            else:
                with self._get_conn() as new_conn:
                    return _execute_save(new_conn)

        except Exception as e:
            logger.error(f"Save Raw Failed: {e}")
            return None

    def batch_save_raw_intelligence(self, items: list) -> int:
        """批量保存原始情报，共享数据库连接和市场快照。"""
        if not items:
            return 0
        
        saved_count = 0
        try:
            # 1. 预解析当前的全局市场快照（利用刚才加的 Redis 缓存）
            now = datetime.now(pytz.utc)
            snaps = {
                "DX-Y.NYB": self.get_market_snapshot("DX-Y.NYB", now),
                "^TNX": self.get_market_snapshot("^TNX", now),
                "^GVZ": self.get_market_snapshot("^GVZ", now),
                "GC=F": self.get_market_snapshot("GC=F", now),
                "CL=F": self.get_market_snapshot("CL=F", now),
            }
            
            # 2. 使用单一连接批量处理
            with self._get_conn() as conn:
                for item in items:
                    try:
                        res = self.save_raw_intelligence(item, market_snapshots=snaps, conn=conn)
                        if res:
                            saved_count += 1
                    except Exception as e:
                        logger.error(f"Batch item save failed: {e}")
            
            return saved_count
        except Exception as e:
            logger.error(f"Batch Save Failed: {e}")
            return 0

    def get_intelligence_analysis(self, source_id: str) -> Optional[dict]:
        """获取单条情报的分析结果 (JSONB 格式)"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT analysis, summary FROM intelligence WHERE source_id = %s", (source_id,))
                    row = cursor.fetchone()
                    if row and row['analysis']:
                        return row['analysis']
                    return None
        except Exception as e:
            logger.error(f"获取情报分析失败 ({source_id}): {e}")
            return None

    def update_lead_analysis(self, source_id, analysis_result):
        """仅更新情报的分析结果和摘要（用于 Lead Evolution 场景）"""
        try:
            def _to_jsonb(val):
                if val is None: return None
                return Jsonb(val)
                
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE intelligence SET
                            summary = %s, 
                            analysis = %s,
                            updated_at = NOW()
                        WHERE source_id = %s
                    """, (
                        analysis_result.get('summary', {}).get('zh', ''),
                        _to_jsonb(analysis_result),
                        source_id
                    ))
        except Exception as e:
            logger.error(f"Lead Evolution 更新失败 ({source_id}): {e}")
            raise e

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

            def _to_jsonb(val):
                if val is None:
                    return None
                return Jsonb(val)

            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    embedding_binary = None
                    if 'embedding' in analysis_result and analysis_result['embedding'] is not None:
                        import pickle
                        embedding_binary = pickle.dumps(analysis_result['embedding'])
                    entities = self._normalize_entities(analysis_result.get('entities'))
                    tags = analysis_result.get('tags')
                    relation_triples = self._normalize_relations(analysis_result.get('relations'))
                    expectation_gap = None
                    agent_trace = analysis_result.get("agent_trace")
                    if agent_trace is not None:
                        expectation_gap = self.compute_expectation_gap(agent_trace)

                    agent_trace = analysis_result.get("agent_trace")
                    if agent_trace is not None:
                        try:
                            cursor.execute("""
                                UPDATE intelligence SET
                                    summary = %s, sentiment = %s, urgency_score = %s,
                                    market_implication = %s, actionable_advice = %s,
                                    sentiment_score = %s, macro_adjustment = %s,
                                    entities = %s,
                                    relation_triples = %s,
                                    agent_trace = %s,
                                    expectation_gap = %s,
                                    embedding = COALESCE(%s, embedding),
                                    status = 'COMPLETED', last_error = NULL
                                WHERE source_id = %s
                            """, (
                                _to_jsonb(analysis_result.get('summary')),
                                _to_jsonb(analysis_result.get('sentiment')),
                                analysis_result.get('urgency_score'),
                                _to_jsonb(analysis_result.get('market_implication')),
                                _to_jsonb(analysis_result.get('actionable_advice')),
                                float(sentiment_score), float(macro_adj),
                                _to_jsonb(entities),
                                _to_jsonb(relation_triples),
                                _to_jsonb(agent_trace),
                                float(expectation_gap) if expectation_gap is not None else None,
                                embedding_binary, source_id,
                            ))
                        except Exception as e:
                            if "agent_trace" in str(e):
                                cursor.execute("""
                                    UPDATE intelligence SET
                                        summary = %s, sentiment = %s, urgency_score = %s,
                                        market_implication = %s, actionable_advice = %s,
                                        sentiment_score = %s, macro_adjustment = %s,
                                        entities = %s,
                                        relation_triples = %s,
                                        expectation_gap = %s,
                                        embedding = COALESCE(%s, embedding),
                                        status = 'COMPLETED', last_error = NULL
                                    WHERE source_id = %s
                                """, (
                                    _to_jsonb(analysis_result.get('summary')),
                                    _to_jsonb(analysis_result.get('sentiment')),
                                    analysis_result.get('urgency_score'),
                                    _to_jsonb(analysis_result.get('market_implication')),
                                    _to_jsonb(analysis_result.get('actionable_advice')),
                                    float(sentiment_score), float(macro_adj),
                                    _to_jsonb(entities),
                                    _to_jsonb(relation_triples),
                                    float(expectation_gap) if expectation_gap is not None else None,
                                    embedding_binary, source_id,
                                ))
                            else:
                                raise
                    else:
                        cursor.execute("""
                            UPDATE intelligence SET
                                summary = %s, sentiment = %s, urgency_score = %s,
                                market_implication = %s, actionable_advice = %s,
                                sentiment_score = %s, macro_adjustment = %s,
                                entities = %s,
                                relation_triples = %s,
                                expectation_gap = %s,
                                embedding = COALESCE(%s, embedding),
                                status = 'COMPLETED', last_error = NULL
                            WHERE source_id = %s
                        """, (
                            _to_jsonb(analysis_result.get('summary')),
                            _to_jsonb(analysis_result.get('sentiment')),
                            analysis_result.get('urgency_score'),
                            _to_jsonb(analysis_result.get('market_implication')),
                            _to_jsonb(analysis_result.get('actionable_advice')),
                            float(sentiment_score), float(macro_adj),
                            _to_jsonb(entities),
                            _to_jsonb(relation_triples),
                            float(expectation_gap) if expectation_gap is not None else None,
                            embedding_binary, source_id,
                        ))
                    conn.commit()
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

            def _to_jsonb(val):
                if val is None:
                    return None
                return Jsonb(val)

            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    entities = self._normalize_entities(analysis_result.get('entities'))
                    tags = analysis_result.get('tags')
                    relation_triples = self._normalize_relations(analysis_result.get('relations'))

                    cursor.execute("""
                        INSERT INTO intelligence (
                            source_id, author, content, summary, sentiment,
                            urgency_score, market_implication, actionable_advice, url,
                            entities, tags, relation_triples,
                            gold_price_snapshot, price_1h, price_24h, timestamp, market_session,
                            clustering_score, exhaustion_score, dxy_snapshot, us10y_snapshot, gvz_snapshot,
                            sentiment_score, fed_regime, macro_adjustment, category
                        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (source_id) DO NOTHING
                    """, (
                        raw_data.get('id'), raw_data.get('author'), raw_data.get('content'),
                        _to_jsonb(analysis_result.get('summary')), _to_jsonb(analysis_result.get('sentiment')),
                        analysis_result.get('urgency_score'),
                        _to_jsonb(analysis_result.get('market_implication')),
                        _to_jsonb(analysis_result.get('actionable_advice')),
                        raw_data.get('url'),
                        _to_jsonb(entities), _to_jsonb(tags), _to_jsonb(relation_triples),
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
                        raw_data.get('category', 'macro_gold'),
                    ))
                    conn.commit()
                    if cursor.rowcount > 0:
                        logger.info(f"💾 Saved Intelligence | Gold: ${gold_price_snapshot}")
        except Exception as e:
            logger.error(f"Save Intelligence Failed: {e}")

    # ── 查询方法 ──────────────────────────────────────────────────────────

    def source_id_exists(self, source_id: str) -> bool:
        """O(1) 查询：source_id 是否已在 intelligence 表中。"""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1 FROM intelligence WHERE source_id = %s LIMIT 1", (source_id,))
                    exists = cursor.fetchone() is not None
            return exists
        except Exception as e:
            logger.warning(f"source_id_exists 查询失败，默认返回 False: {e}")
            return False

    def source_ids_batch_exists(self, source_ids: list) -> set:
        """批量查询一组 source_id 是否已存在，返回已存在的 ID 集合。"""
        if not source_ids:
            return set()
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT source_id FROM intelligence WHERE source_id = ANY(%s)", (source_ids,))
                    rows = cursor.fetchall()
            return {row["source_id"] for row in rows}
        except Exception as e:
            logger.warning(f"source_ids_batch_exists 查询失败，返回空集合: {e}")
            return set()

    def get_recent_intelligence(self, limit=10):
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT * FROM intelligence ORDER BY timestamp DESC LIMIT %s", (limit,))
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Recent Failed: {e}")
            return []

    def get_pending_intelligence(self, limit=20):
        """Fetch records that need AI analysis or retries."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT * FROM intelligence
                        WHERE status IN ('PENDING', 'FAILED')
                        ORDER BY timestamp DESC LIMIT %s
                    """, (limit,))
                    rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Get Pending Failed: {e}")
            return []

    def update_intelligence_status(self, source_id, status, error=None):
        """Update the lifecycle status of an intelligence item."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE intelligence SET status = %s, last_error = %s WHERE source_id = %s
                    """, (status, error, source_id))
                    conn.commit()
        except Exception as e:
            logger.error(f"Update Status Failed: {e}")

    def check_analysis_exists(self, source_id):
        """Check if a record already has AI analysis data."""
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        "SELECT 1 FROM intelligence WHERE source_id = %s AND summary IS NOT NULL LIMIT 1",
                        (source_id,)
                    )
                    exists = cursor.fetchone() is not None
            return exists
        except:
            return False

    def is_duplicate(self, new_url, new_content, new_summary=None, vector=None) -> dict:
        """
        判断情报是否重复。
        返回 dict: {is_duplicate: bool, status: 'DUP'|'SUSPECTED'|'NEW', lead_id: int, lead_summary: str}
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    # 1. URL 绝对重复校验
                    cursor.execute("SELECT id FROM intelligence WHERE url = %s LIMIT 1", (new_url,))
                    row = cursor.fetchone()
                    if row:
                        logger.info(f"🚫 URL {new_url} 已存在，跳过。")
                        return {"is_duplicate": True, "status": "DUP", "lead_id": row['id']}
                    
                    # 2. 向量语义重复校验 (HNSW)
                    if vector is not None:
                        result = self.is_semantic_duplicate(vector)
                        if result["status"] == "DUP":
                            logger.info(f"🚫 发现语义重复 (HNSW ID: {result.get('lead_id')}, 分数: {result.get('sim', 0):.2f})")
                            return {"is_duplicate": True, "status": "DUP", "lead_id": result.get('lead_id')}
                        
                        if result["status"] == "SUSPECTED":
                            logger.info(f"⚖️ 发现疑似重复 (HNSW ID: {result.get('lead_id')}, 分数: {result.get('sim', 0):.2f})，进入 Delta 判定。")
                            return {
                                "is_duplicate": False, 
                                "status": "SUSPECTED", 
                                "lead_id": result.get('lead_id'),
                                "lead_summary": result.get('lead_summary')
                            }
            
            return {"is_duplicate": False, "status": "NEW"}
        except Exception as e:
            logger.error(f"Duplicate Check 综合判定失败: {e}")
            return {"is_duplicate": False, "status": "ERROR"}

    # ── 事件聚类支持方法 ──────────────────────────────────────────────────

    def find_similar_pairs(self, source_ids: list, threshold: float = 0.45, time_window_hours: int = 48) -> list:
        """
        在给定的 source_ids 范围内查找相似对。
        Story Threading 优化：引入衰减式时间窗口。
        相似度随时间差增加按指数衰减，以支持长周期的故事线追踪（最长 48h）。
        """
        if len(source_ids) < 2:
            return []
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    # 使用 exp(-dt/T) 实现衰减，T = 12h (43200s)
                    # 只有 (相似度 * 衰减因子) > threshold 的才会被聚类
                    cursor.execute("""
                        SELECT a.source_id AS source_id_a, b.source_id AS source_id_b
                        FROM intelligence a
                        JOIN intelligence b ON a.source_id < b.source_id
                        WHERE a.source_id = ANY(%s) AND b.source_id = ANY(%s)
                          AND ABS(EXTRACT(EPOCH FROM (a.timestamp - b.timestamp))) < %s
                          AND (
                            (a.embedding_vec IS NOT NULL AND b.embedding_vec IS NOT NULL 
                             AND ((1 - (a.embedding_vec <=> b.embedding_vec)) * exp(-ABS(EXTRACT(EPOCH FROM (a.timestamp - b.timestamp))) / 43200.0)) > %s)
                            OR
                            ((a.embedding_vec IS NULL OR b.embedding_vec IS NULL) 
                             AND (similarity(COALESCE(a.content, ''), COALESCE(b.content, '')) * exp(-ABS(EXTRACT(EPOCH FROM (a.timestamp - b.timestamp))) / 43200.0)) > %s)
                          )
                    """, (source_ids, source_ids, time_window_hours * 3600, threshold, threshold))
                    rows = cursor.fetchall()
            return [(r["source_id_a"], r["source_id_b"]) for r in rows]
        except Exception as e:
            logger.error(f"find_similar_pairs (Story Threading) failed: {e}")
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
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
                    logger.info(
                        f"🔗 事件聚类 [{cluster_id[:8]}] | lead={lead_source_id[:20]} | "
                        f"suppressed={len(follower_ids)} 条"
                    )
        except Exception as e:
            logger.error(f"mark_clustered 失败: {e}")

    # ── 事件知识图谱 ──────────────────────────────────────────────────────

    def _upsert_entity_node(self, cursor, entity_name: str, entity_type: str = "unknown") -> int | None:
        """
        根据名称和类型 Upsert 实体节点。
        使用标准化后的 normalized_name 作为唯一冲突检查，但保留展示用的 entity_name。
        """
        clean_name = (entity_name or "").strip()
        if not clean_name:
            return None

        canonical_name = normalize_entity_name(clean_name)
        normalized_name = canonical_name.strip().lower()
        # 针对 Gold/Oil 等资产强制标准化类型
        canonical_type = normalize_entity_type(canonical_name, entity_type)

        cursor.execute("""
            INSERT INTO entity_nodes (entity_name, normalized_name, entity_type)
            VALUES (%s, %s, %s)
            ON CONFLICT (normalized_name, entity_type)
            DO UPDATE SET entity_name = EXCLUDED.entity_name
            RETURNING node_id
        """, (canonical_name, normalized_name, canonical_type))
        res = cursor.fetchone()
        return res["node_id"] if res else None

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
            Jsonb(metadata or {}),
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
            "id": row.get("id") if hasattr(row, 'get') else row[0],
            "source_id": row.get("source_id") if hasattr(row, 'get') else row[1],
            "event_cluster_id": row.get("event_cluster_id") if hasattr(row, 'get') else row[2],
            "urgency_score": row.get("urgency_score") if hasattr(row, 'get') else row[3],
            "source_credibility_score": row.get("source_credibility_score") if hasattr(row, 'get') else row[4],
            "timestamp": row.get("timestamp") if hasattr(row, 'get') else row[5],
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    context = self._get_intelligence_context(cursor, source_id)
                    if not context:
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
                    logger.info(f"🕸️ 图谱写入完成: source_id={source_id}, entities={len(entities)}, relations={len(relations)}")
        except Exception as e:
            logger.error(f"图谱写入失败 [{source_id}]: {e}")

    def refresh_relation_rule_stats(self, limit: int = 5000) -> None:
        """
        基于历史 outcome 对关系规则做简单学习，更新 relation_rule_stats.weight。
        """
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT relation, weight
                        FROM relation_rule_stats
                        WHERE relation = ANY(%s)
                    """, (normalized,))
                    rows = cursor.fetchall()
            return {row["relation"]: float(row["weight"]) for row in rows}
        except Exception as e:
            logger.error(f"get_relation_rule_weights 失败: {e}")
            return {}

    def get_event_graph(self, event_cluster_id: str) -> dict:
        """按 event_cluster_id 获取图谱节点、边与可解释推理链。"""
        if not event_cluster_id:
            return {"nodes": [], "edges": [], "inferences": [], "evidence": []}
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:

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
        """按实体名称返回邻接子图（聚合所有同名节点）。"""
        if not entity_name:
            return {"center": None, "nodes": [], "edges": []}
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    # 1. 查找所有匹配该名称的节点 ID（支持类型聚合）
                    cursor.execute("""
                        SELECT node_id, entity_name, entity_type
                        FROM entity_nodes
                        WHERE normalized_name = %s
                    """, (entity_name.strip().lower(),))
                    nodes_data = cursor.fetchall()
                    if not nodes_data:
                        return {"center": None, "nodes": [], "edges": []}

                    node_ids = [n["node_id"] for n in nodes_data]
                    # 以第一个节点作为中心展示信息
                    center_info = dict(nodes_data[0])

                    # 2. 查询这些 ID 集合的所有关联边
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
                        WHERE e.from_node_id = ANY(%s) OR e.to_node_id = ANY(%s)
                        ORDER BY e.confidence_score DESC, e.strength DESC
                        LIMIT %s
                    """, (node_ids, node_ids, max(1, limit)))
                    edges = [dict(row) for row in cursor.fetchall()]

                    # 3. 收集所有相关节点
                    node_map = {}
                    for n in nodes_data:
                        node_map[n["node_id"]] = dict(n)
                        
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

            return {"center": center_info, "nodes": list(node_map.values()), "edges": edges}
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
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
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

