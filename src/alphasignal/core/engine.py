import time
import json
import asyncio
from datetime import datetime
import pytz
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger

# 引入组件
from src.alphasignal.providers.llm.gemini import GeminiLLM
from src.alphasignal.providers.llm.deepseek import DeepSeekLLM
from src.alphasignal.providers.channels.email import EmailChannel
from src.alphasignal.providers.channels.bark import BarkChannel
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.backtest import BacktestEngine
from src.alphasignal.core.deduplication import NewsDeduplicator
from src.alphasignal.core.event_clusterer import EventClusterer

class AlphaEngine:
    """
    AI 分析消费者。
    不再负责采集，只消费 intelligence 表中 status=PENDING 的记录。
    RSS 采集由独立的 RSSCollector（run_collector.py）负责。
    """
    def __init__(self):
        self.db = IntelligenceDB()
        
        # 显式初始化 LLM 引擎，根据配置文件动态选择主力模型
        provider = settings.AI_PROVIDER.lower()
        if provider == "deepseek":
            self.primary_llm = DeepSeekLLM()
            self.fallback_llm = GeminiLLM()
            logger.info("🧠 选用 API: DeepSeek 作为主力 AI 引擎")
        elif provider == "openai":
            from src.alphasignal.providers.llm.openai_llm import OpenAILLM # 假设存在
            self.primary_llm = OpenAILLM()
            self.fallback_llm = DeepSeekLLM()
            logger.info("🧠 选用 API: OpenAI 作为主力 AI 引擎")
        else: # 默认 gemini 
            self.primary_llm = GeminiLLM()
            self.fallback_llm = DeepSeekLLM()
            logger.info("🧠 选用 API: Gemini 作为主力 AI 引擎")
            
        self.channels     = [EmailChannel(), BarkChannel()]
        self.backtester   = BacktestEngine(self.db)
        self.clusterer    = EventClusterer(db=self.db)
        self.deduplicator = NewsDeduplicator(db=self.db)
        self._round_snapshot = {}
        # Concurrency Control
        self.ai_semaphore = asyncio.Semaphore(5)
        # Bootstrap deduplicator history from DB
        self._bootstrap_deduplicator()
        
    def _bootstrap_deduplicator(self):
        """Load recent intelligence from DB to initialize deduplicator history"""
        logger.info("🧵正在初始化去重引擎历史数据 (SimHash)...")
        try:
            recent_items = self.db.get_recent_intelligence(limit=200)
            if recent_items:
                from simhash import Simhash
                for item in reversed(recent_items):
                    summary = item.get('summary')
                    summary_text = ""
                    if isinstance(summary, dict):
                        summary_text = summary.get('en', '') or str(summary)
                    elif isinstance(summary, str):
                        summary_text = summary
                    
                    text = summary_text if len(summary_text) > 20 else (item.get('content') or "")
                    if text:
                        clean_text = self.deduplicator.normalize(text)
                        if clean_text:
                            sh = Simhash(clean_text)
                            # 仅预热 SimHash 粗筛历史。语义精筛改由 pgvector 接管，无需预热到内存。
                            self.deduplicator.add_to_history(sh, vector=None, record_id=item.get('id'))
                
                logger.info(f"✅ 已加载 {len(self.deduplicator.simhash_history)} 条记录到 SimHash 历史。")
        except Exception as e:
            logger.error(f"❌ 初始化去重引擎失败: {e}")

    async def run_once_async(self):
        """
        核心异步流水线（纯分析消费者）。
        RSS 采集已由独立的 RSSCollector 负责，本方法直接处理 PENDING 记录。
        """
        logger.info(">>> 启动情报分析...")

        # 0. 异步同步收益率 + 更新信源可信度
        await asyncio.to_thread(self.backtester.sync_outcomes)
        await asyncio.to_thread(self.db.compute_source_credibility)

        # 1. 获取所有待分析记录 (PENDING/FAILED)
        pending_records = await asyncio.to_thread(self.db.get_pending_intelligence, limit=50)

        if not pending_records:
            logger.info("无待分析情报，本轮结束。")
            return

        # 2. 市场快照已经由 Collector 注入在 PENDING 记录中，Worker 无需重复抓取
        # 移除了原有的 fetch_round_snapshot 冗余逻辑

        # 2.5 事件聚类：同一事件多信源 → 只保留 lead 进 AI 分析
        lead_records, n_clustered = await asyncio.to_thread(
            self.clusterer.cluster, pending_records
        )
        if n_clustered > 0:
            logger.info(f"🔗 聚类压制 {n_clustered} 条重复信源报道，本轮仅分析 {len(lead_records)} 条")

        # 3. AI 并发分析
        enriched_items = lead_records
        for item in enriched_items:
            item.setdefault('extraction_method', 'RSS_SUMMARY')

        logger.info(f"🚀 并行分析中 (并发数: 5, 任务数: {len(enriched_items)})...")
        tasks = [self._process_single_item_async(item) for item in enriched_items]
        await asyncio.gather(*tasks)
        logger.info("<<< 本轮分析完成。")

    async def _process_single_item_async(self, raw_data):
        """单条情报的异步处理状态机"""
        source_id = raw_data.get('source_id') or raw_data.get('id')
        
        async with self.ai_semaphore:
            try:
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'PROCESSING')
                
                # 1. 注入上下文
                await asyncio.to_thread(self._enrich_market_context, raw_data)
                
                # 2. 语义去重
                is_dup = await asyncio.to_thread(self.deduplicator.is_duplicate, raw_data.get('content'))
                if is_dup:
                    logger.info(f"🚫 语义重复，标记为已过滤: {source_id}")
                    await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'COMPLETED', 'Deduplicated')
                    return

                # 去重通过后，将计算好的向量持久化到 pgvector（供后续新闻比对用）
                if self.deduplicator.last_vector is not None:
                    await asyncio.to_thread(
                        self.db.save_embedding_vec, source_id, self.deduplicator.last_vector
                    )

                # 3. AI 分析
                logger.info(f"🤖 正在分析({raw_data.get('extraction_method', 'UNKNOWN')}): {source_id}")
                try:
                    # 显式使用 self.primary_llm，确保它是 AlphaEngine 的属性
                    analysis_result = await self.primary_llm.analyze_async(raw_data)
                except Exception as e:
                    logger.warning(f"Primary LLM failed for {source_id}, trying fallback: {e}")
                    analysis_result = await self.fallback_llm.analyze_async(raw_data)

                # 4. 存储分析结果
                if analysis_result:
                    analysis_result['embedding'] = self.deduplicator.last_vector
                    await asyncio.to_thread(self.db.update_intelligence_analysis, source_id, analysis_result, raw_data)
                    await self._trigger_trade_and_dispatch(analysis_result, raw_data)
                else:
                    raise ValueError("AI analysis returned empty result")
                
            except Exception as e:
                logger.error(f"处理条目失败 {source_id}: {e}")
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'FAILED', str(e))

    async def _trigger_trade_and_dispatch(self, analysis_result, raw_data):
        sentiment_score = analysis_result.get('sentiment_score', 0)
        signal_direction = 'Neutral'
        if sentiment_score >= 0.3:
            signal_direction = 'Long'
        elif sentiment_score <= -0.3:
            signal_direction = 'Short'
        else:
            signal_direction = self._parse_sentiment(analysis_result.get('sentiment'))

        if signal_direction in ['Long', 'Short']:
            trade_initiated = await asyncio.to_thread(self.backtester.process_signal, signal_direction)
            if trade_initiated:
                logger.info(f"✅ 🟢 触发交易信号: {signal_direction} (ID: {raw_data.get('id')})")

        urgency = int(analysis_result.get('urgency_score', 5))
        if urgency >= 7:
            await asyncio.to_thread(self._dispatch, analysis_result, raw_data)
        else:
            logger.debug(f"ℹ️ 情报 (Urgency: {urgency}) 已入库但不推送。")

    def run_once(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_once_async())
        finally:
            loop.close()

    def _enrich_market_context(self, raw_data):
        from src.alphasignal.utils.market_calendar import is_gold_market_open
        now = datetime.now(pytz.utc)

        market_open = is_gold_market_open(now)
        status_label = "🟢 正在交易 (OPEN)" if market_open else "🔴 已休市 (CLOSED - Weekend/Holiday)"

        dxy = (
            raw_data.get('dxy_snapshot')
            or self._round_snapshot.get('dxy_snapshot')
            or self.db.get_market_snapshot("DX-Y.NYB", now)
        )
        gvz = (
            raw_data.get('gvz_snapshot')
            or self._round_snapshot.get('gvz_snapshot')
            or self.db.get_market_snapshot("^GVZ", now)
        )
        tnx = (
            raw_data.get('us10y_snapshot')
            or self.db.get_market_snapshot("^TNX", now)
        )
        oil = (
            raw_data.get('oil_price_snapshot')
            or self.db.get_market_snapshot("CL=F", now)
        )

        cot = self.db.get_latest_indicator("COT_GOLD_NET", now)
        cot_info = "N/A"
        if cot:
            sentiment = "拥挤/超买" if cot['percentile'] > 85 else "冷淡/超卖" if cot['percentile'] < 15 else "中性"
            cot_info = f"{cot['percentile']}% (状态: {sentiment})"

        fed = self.db.get_latest_indicator("FED_REGIME", now)
        fed_context = "中性 (Neutral)"
        if fed:
            fed_context = "降息周期/鸽派 (Dovish)" if fed['value'] > 0 else "加息周期/鹰派 (Hawkish)" if fed['value'] < 0 else "中性 (Neutral)"

        context = f"""
[当前市场环境快照]:
- 市场交易状态: {status_label}
- 美元指数 (DXY): {dxy if dxy is not None else '获取中'}
- 美债10年期收益率 (TNX): {tnx if tnx is not None else '获取中'}%
- WTI原油 (Oil): {oil if oil is not None else '获取中'}
- 黄金波动率 (GVZ): {gvz if gvz is not None else '暂无'}
- 基金持仓拥挤度 (COT): {cot_info}
- 美联储宏观基调 (Regime): {fed_context}
"""
        raw_data['context'] = context
        raw_data['market_open'] = market_open
        raw_data['dxy_snapshot'] = dxy
        raw_data['gvz_snapshot'] = gvz
        raw_data['us10y_snapshot'] = tnx
        raw_data['oil_price_snapshot'] = oil
        raw_data['fed_val'] = fed['value'] if fed else 0
        
        return context

    def _dispatch(self, analysis_data, raw_data):
        sentiment_text = ""
        sentiment = analysis_data.get('sentiment', {})
        if isinstance(sentiment, dict):
            sentiment_text = sentiment.get('zh') or sentiment.get('en') or "情报分析"
        else:
            sentiment_text = str(sentiment)

        title = f"【AlphaSignal】{sentiment_text}"
        body = self._format_message(analysis_data)
        
        url = raw_data.get('url')
        db_id = raw_data.get('id')
        
        for channel in self.channels:
            try:
                channel.send(title, body, source_url=url, db_id=db_id)
            except Exception as e:
                logger.warning(f"❌ Failed to dispatch to {channel.__class__.__name__} [ID: {db_id}]: {e}")

    def _parse_sentiment(self, sentiment_json) -> str:
        try:
            if isinstance(sentiment_json, str):
                try:
                    data = json.loads(sentiment_json.replace("'", '"'))
                except:
                    data = {'en': sentiment_json}
            else:
                data = sentiment_json
                
            text = str(data.get('en', '')).lower()
            if 'bullish' in text or 'safe-haven' in text or 'positive' in text or 'upward' in text:
                return 'Long'
            if 'bearish' in text or 'negative' in text or 'downward' in text or 'pressure' in text:
                return 'Short'
            return 'Neutral'
        except:
            return 'Neutral'

    def _format_message(self, data):
        market_impact_str = ""
        market_implication = data.get('market_implication', {})
        if isinstance(market_implication, dict):
            zh_impact = market_implication.get('zh')
            if zh_impact:
                market_impact_str = zh_impact
            else:
                for asset, impact in market_implication.items():
                    market_impact_str += f"🔹 {asset}: {impact}\n"
        else:
            market_impact_str = str(market_implication)

        summary = data.get('summary', '')
        if isinstance(summary, dict): summary = summary.get('zh') or summary.get('en')

        advice = data.get('actionable_advice', '')
        if isinstance(advice, dict): advice = advice.get('zh') or advice.get('en')

        return f"""
🚨 【AlphaSignal 投资快报】
--------------------------------------------
📌 [核心摘要]
{summary}

📊 [市场深度影响]
{market_impact_str.strip()}

💡 [实战策略建议]
{advice}

🔗 [原文来源及链接]
{data.get('url')}
--------------------------------------------
(此消息由 AlphaSignal AI 实时生成，仅供参考)
"""
