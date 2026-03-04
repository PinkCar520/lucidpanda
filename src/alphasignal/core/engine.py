import time
import json
import asyncio
from datetime import datetime
import pytz
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger

# 引入组件
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
        self.db = IntelligenceDB()
        self.sources = [
            RSSHubSource(db=self.db),
        ]
        
        # 显式初始化 LLM 引擎，确保不遗漏
        self.primary_llm = GeminiLLM()
        self.fallback_llm = DeepSeekLLM()
        
        self.channels     = [EmailChannel(), BarkChannel()]
        self.backtester   = BacktestEngine(self.db)
        self.deduplicator = NewsDeduplicator(db=self.db)
        self._round_snapshot = {}  # 轮次市场快照缓存，每轮 fetch 一次供所有条目共用
        
        # Concurrency Control
        self.ai_semaphore = asyncio.Semaphore(5) # Limit to 5 concurrent AI calls
        
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

    def _fetch_round_snapshot(self) -> dict:
        """
        每轮扫描调用一次，获取当前实时市场快照。
        """
        now = datetime.now(pytz.utc)
        snapshot = {
            'dxy_snapshot':        self.db.get_market_snapshot("DX-Y.NYB", now),
            'us10y_snapshot':      self.db.get_market_snapshot("^TNX",     now),
            'gvz_snapshot':        self.db.get_market_snapshot("^GVZ",     now),
            'gold_price_snapshot': self.db.get_market_snapshot("GC=F",     now),
        }
        logger.info(
            f"📊 本轮市场快照 | "
            f"Gold={snapshot['gold_price_snapshot']} | "
            f"DXY={snapshot['dxy_snapshot']} | "
            f"GVZ={snapshot['gvz_snapshot']}"
        )
        return snapshot

    async def run_once_async(self):
        """核心异步流水线"""
        logger.info(">>> 启动流式情报扫描...")
        
        # 0. 异步同步收益率
        await asyncio.to_thread(self.backtester.sync_outcomes)

        # 1. 发现新情报（直接调用 fetch_async，全程在事件循环内并发执行）
        discovered_items = []
        for source in self.sources:
            try:
                # 优先使用 fetch_async()（并发版），兜底使用同步 fetch()
                if hasattr(source, 'fetch_async'):
                    items = await source.fetch_async()
                else:
                    items = await asyncio.to_thread(source.fetch)
                if items:
                    discovered_items.extend(items if isinstance(items, list) else [items])
            except Exception as e:
                logger.error(f"数据源发现异常: {e}")

        # 1.5 URL 去重
        seen_urls: set = set()
        unique_items: list = []
        for item in discovered_items:
            url = item.get("url", "") or item.get("id", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)
        discovered_items = unique_items

        # 1.75 注入快照
        if discovered_items:
            self._round_snapshot = await asyncio.to_thread(self._fetch_round_snapshot)
            for item in discovered_items:
                item.setdefault('gold_price_snapshot', self._round_snapshot.get('gold_price_snapshot'))
                item.setdefault('dxy_snapshot',        self._round_snapshot.get('dxy_snapshot'))
                item.setdefault('us10y_snapshot',      self._round_snapshot.get('us10y_snapshot'))
                item.setdefault('gvz_snapshot',        self._round_snapshot.get('gvz_snapshot'))

        # 2. 入库并标记为 PENDING
        for item in discovered_items:
            await asyncio.to_thread(self.db.save_raw_intelligence, item)

        # 3. 获取所有待分析记录 (PENDING/FAILED)
        pending_records = await asyncio.to_thread(self.db.get_pending_intelligence, limit=50)
        
        if not pending_records:
            logger.info("无待分析情报，本轮结束。")
            return

        # 4. 分析
        enriched_items = pending_records
        for item in enriched_items:
            item.setdefault('extraction_method', 'RSS_SUMMARY')

        # 5. 并行并发 AI 分析
        logger.info(f"🚀 并行分析中 (并发数: 5, 任务数: {len(enriched_items)})...")
        tasks = [self._process_single_item_async(item) for item in enriched_items]
        await asyncio.gather(*tasks)
        logger.info("<<< 本轮流式扫描完成。")

    async def _process_single_item_async(self, raw_data):
        """单条情报的异步处理状态机"""
        source_id = raw_data.get('source_id') or raw_data.get('id')
        
        async with self.ai_semaphore:
            try:
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'PROCESSING')
                
                # 1. 注入上下文
                await asyncio.to_thread(self._enrich_market_context, raw_data)
                
                # 2. 语义去重
                if self.deduplicator.is_duplicate(raw_data.get('content')):
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
- 美元指数 (DXY): {dxy if dxy else '获取中'}
- 黄金波动率 (GVZ): {gvz if gvz else '获取中'}
- 基金持仓拥挤度 (COT): {cot_info}
- 美联储宏观基调 (Regime): {fed_context}
"""
        raw_data['context'] = context
        raw_data['market_open'] = market_open
        raw_data['dxy_snapshot'] = dxy
        raw_data['gvz_snapshot'] = gvz
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
