import time
import json
import asyncio
from datetime import datetime
import pytz
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger

# 引入组件
from src.alphasignal.providers.data_sources.google_news import GoogleNewsSource
from src.alphasignal.providers.data_sources.rsshub import RSSHubSource
from src.alphasignal.providers.llm.gemini import GeminiLLM
from src.alphasignal.providers.llm.deepseek import DeepSeekLLM
from src.alphasignal.providers.channels.email import EmailChannel
from src.alphasignal.providers.channels.bark import BarkChannel
from src.alphasignal.core.database import IntelligenceDB
from src.alphasignal.core.backtest import BacktestEngine
from src.alphasignal.core.deduplication import NewsDeduplicator

class AlphaEngine:
    def __init__(self):
        self.sources = [
            GoogleNewsSource(),
            RSSHubSource()
        ]
        self.primary_llm = GeminiLLM()
        self.fallback_llm = DeepSeekLLM()
        self.channels = [EmailChannel(), BarkChannel()]
        self.db = IntelligenceDB()
        self.backtester = BacktestEngine(self.db)
        self.deduplicator = NewsDeduplicator()
        
        # Concurrency Control
        self.ai_semaphore = asyncio.Semaphore(5) # Limit to 5 concurrent AI calls
        
        # Bootstrap deduplicator history from DB
        self._bootstrap_deduplicator()
        
    def _bootstrap_deduplicator(self):
        """Load recent intelligence from DB to initialize deduplicator history"""
        logger.info("🧵正在初始化去重引擎历史数据...")
        try:
            # Load intelligence from the last 24 hours
            recent_items = self.db.get_recent_intelligence(limit=200)
            if recent_items:
                # Process from oldest to newest to maintain correct history order
                for item in reversed(recent_items):
                    # Combine summary and content for consistent matching
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
                            from simhash import Simhash
                            sh = Simhash(clean_text)
                            
                            # --- Persistent Embedding Cache Logic ---
                            vec = None
                            db_vec_binary = item.get('embedding')
                            
                            if db_vec_binary:
                                try:
                                    import pickle
                                    vec = pickle.loads(db_vec_binary)
                                except Exception as e:
                                    logger.warning(f"Failed to deserialize embedding for ID {item.get('id')}: {e}")
                            
                            # Fallback if no cache in DB
                            if vec is None and self.deduplicator.model:
                                try:
                                    vec = self.deduplicator.model.encode(clean_text)
                                except Exception as e:
                                    logger.warning(f"Semantic encoding failed during bootstrap: {e}")
                            
                            self.deduplicator.add_to_history(sh, vec, record_id=item.get('id'))
                
                logger.info(f"✅ 已加载 {len(self.deduplicator.simhash_history)} 条记录到去重引擎历史。")
        except Exception as e:
            logger.error(f"❌ 初始化去重引擎失败: {e}")

    async def run_once_async(self):
        """
        核心异步流水线：
        1. 发现新情报 (Discovery)
        2. 全文抓取 (Enrichment)
        3. 状态检查与补课 (Reconciliation)
        4. 并行 AI 分析 (Analysis)
        """
        logger.info(">>> 启动流式情报扫描...")
        
        # 0. 异步同步收益率
        await asyncio.to_thread(self.backtester.sync_outcomes)

        # 1. 同步发现新情报 (Discovery Phase)
        discovered_items = []
        for source in self.sources:
            try:
                items = await asyncio.to_thread(source.fetch)
                if items:
                    discovered_items.extend(items if isinstance(items, list) else [items])
            except Exception as e:
                logger.error(f"数据源发现异常: {e}")

        # 2. 初始入库并标记为 PENDING
        for item in discovered_items:
            await asyncio.to_thread(self.db.save_raw_intelligence, item)

        # 3. 补课机制：获取所有未完成分析的记录 (PENDING/FAILED)
        pending_records = await asyncio.to_thread(self.db.get_pending_intelligence, limit=20)
        
        if not pending_records:
            logger.info("无待分析情报，本轮结束。")
            return

        # 4. 深度提取全文 (只针对待分析的)
        from src.alphasignal.utils.crawler import AsyncRichCrawler
        crawler = AsyncRichCrawler()
        enriched_items = await crawler.batch_crawl(pending_records)

        # 5. 并行并发 AI 分析
        logger.info(f"🚀 并行分析中 (并发数: 5, 任务数: {len(enriched_items)})...")
        tasks = []
        for item in enriched_items:
            tasks.append(self._process_single_item_async(item))
        
        await asyncio.gather(*tasks)
        logger.info("<<< 本轮流式扫描完成。")

    async def _process_single_item_async(self, raw_data):
        """单条情报的异步处理状态机"""
        source_id = raw_data.get('source_id') or raw_data.get('id')
        
        async with self.ai_semaphore:
            try:
                # 标记为 PROCESSING 防止竞争
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'PROCESSING')
                
                # 1. 注入上下文 (同步方法转异步)
                context_str = await asyncio.to_thread(self._enrich_market_context, raw_data)
                
                # 2. 语义去重 (BERT级别)
                if self.deduplicator.is_duplicate(raw_data.get('content')):
                    logger.info(f"🚫 语义重复，标记为已过滤: {source_id}")
                    await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'COMPLETED', 'Deduplicated')
                    return

                # 3. AI 分析 (异步)
                logger.info(f"🤖 正在分析({raw_data.get('extraction_method', 'UNKNOWN')}): {source_id}")
                try:
                    analysis_result = await self.primary_llm.analyze_async(raw_data)
                except Exception as e:
                    logger.warning(f"Primary LLM failed for {source_id}, trying fallback: {e}")
                    analysis_result = await self.fallback_llm.analyze_async(raw_data)

                # 4. 存储分析结果并标记为 COMPLETED
                if analysis_result:
                    analysis_result['embedding'] = self.deduplicator.last_vector
                    await asyncio.to_thread(self.db.update_intelligence_analysis, source_id, analysis_result, raw_data)

                    # 5. 交易逻辑与分发
                    await self._trigger_trade_and_dispatch(analysis_result, raw_data)
                else:
                    raise ValueError("AI analysis returned empty result")
                
            except Exception as e:
                logger.error(f"处理条目失败 {source_id}: {e}")
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'FAILED', str(e))

    async def _trigger_trade_and_dispatch(self, analysis_result, raw_data):
        """异步化的交易触发与分发"""
        signal_direction = self._parse_sentiment(analysis_result.get('sentiment'))
        if signal_direction in ['Long', 'Short']:
            trade_initiated = await asyncio.to_thread(self.backtester.process_signal, signal_direction)
            if trade_initiated:
                logger.info(f"✅ 触发交易信号: {signal_direction} (ID: {raw_data.get('id')})")

        # 多渠道分发
        await asyncio.to_thread(self._dispatch, analysis_result)

    def run_once(self):
        """兼容性包装器，调用异步方法"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.run_once_async())
        finally:
            loop.close()

    def _enrich_market_context(self, raw_data):
        """注入多维度市场背景数据 (DXY, GVZ, COT)"""
        now = datetime.now(pytz.utc)
        
        # 1. 实时行情快照
        dxy = self.db.get_market_snapshot("DX-Y.NYB", now)
        gvz = self.db.get_market_snapshot("^GVZ", now)
        
        # 2. 持仓数据 (Dimension B)
        cot = self.db.get_latest_indicator("COT_GOLD_NET", now)
        cot_info = "N/A"
        if cot:
            sentiment = "拥挤/超买" if cot['percentile'] > 85 else "冷淡/超卖" if cot['percentile'] < 15 else "中性"
            cot_info = f"{cot['percentile']}% (状态: {sentiment})"

        # 3. 宏观政策背景 (Dimension D - Fed Backdrop)
        fed = self.db.get_latest_indicator("FED_REGIME", now)
        fed_context = "中性 (Neutral)"
        if fed:
            fed_context = "降息周期/鸽派 (Dovish)" if fed['value'] > 0 else "加息周期/鹰派 (Hawkish)" if fed['value'] < 0 else "中性 (Neutral)"

        context = f"""
[当前市场环境快照]:
- 美元指数 (DXY): {dxy if dxy else '获取中'}
- 黄金波动率 (GVZ): {gvz if gvz else '获取中'} (指数 > 25 表示恐慌/流动性枯竭风险)
- 基金持仓拥挤度 (COT): {cot_info}
- 美联储宏观基调 (Regime): {fed_context}
"""
        raw_data['context'] = context
        raw_data['dxy_snapshot'] = dxy
        raw_data['gvz_snapshot'] = gvz
        raw_data['fed_val'] = fed['value'] if fed else 0
        
        return context

    def _dispatch(self, data):
        sentiment_text = ""
        sentiment = data.get('sentiment')
        if isinstance(sentiment, dict):
            sentiment_text = sentiment.get('zh') or sentiment.get('en') or "情报分析"
        else:
            sentiment_text = str(sentiment)

        title = f"【AlphaSignal】{sentiment_text}"
        body = self._format_message(data)
        
        for channel in self.channels:
            try:
                channel.send(title, body)
            except Exception as e:
                logger.warning(f"Failed to dispatch to {channel.__class__.__name__}: {e}")

    def _parse_sentiment(self, sentiment_json) -> str:
        """根据情绪文本确定交易方向"""
        try:
            if isinstance(sentiment_json, str):
                try:
                    data = json.loads(sentiment_json.replace("'", '"'))
                except json.JSONDecodeError:
                    data = {'en': sentiment_json}
            else:
                data = sentiment_json
                
            text = str(data.get('en', '')).lower()
            
            if 'bullish' in text or 'safe-haven' in text or 'positive' in text or 'upward' in text:
                return 'Long'
            if 'bearish' in text or 'negative' in text or 'downward' in text or 'pressure' in text:
                return 'Short'
                
            return 'Neutral'
        except Exception as e:
            logger.warning(f"解析情绪失败: {e}, 默认为中性。")
            return 'Neutral'

    def _format_message(self, data):
        market_impact_str = ""
        market_implication = data.get('market_implication', {})
        
        if isinstance(market_implication, dict):
            # Try to get localized version or iterate
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
