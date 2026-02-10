import time
import json
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
                        # We don't use is_duplicate here to avoid redundant checks, 
                        # just populate the internal history
                        clean_text = self.deduplicator.normalize(text)
                        if clean_text:
                            from simhash import Simhash
                            sh = Simhash(clean_text)
                            vec = None
                            if self.deduplicator.model:
                                try:
                                    vec = self.deduplicator.model.encode(clean_text)
                                except Exception as e:
                                    logger.warning(f"Semantic encoding failed during bootstrap: {e}")
                            
                            self.deduplicator.add_to_history(sh, vec, record_id=item.get('id'))
                
                logger.info(f"✅ 已加载 {len(self.deduplicator.simhash_history)} 条记录到去重引擎历史。")
        except Exception as e:
            logger.error(f"❌ 初始化去重引擎失败: {e}")

        
    def run_once(self):
        logger.info(">>> 开始一轮新的情报扫描...")
        
        # 0. 数据回填
        self.backtester.sync_outcomes()

        # 1. 获取所有数据源的新情报
        new_items = []
        for source in self.sources:
            try:
                items = source.fetch()
                if items:
                    if isinstance(items, list):
                        new_items.extend(items)
                    else:
                        new_items.append(items)
            except Exception as e:
                logger.error(f"数据源扫描异常: {e}")

        if not new_items:
            logger.info("无新情报，本轮结束。")
            return

        logger.info(f"本轮共发现 {len(new_items)} 条新情报，开始逐一处理...")

        # 2. 逐条处理
        for raw_data in new_items:
            self._process_single_item(raw_data)
            
        logger.info("<<< 本轮扫描完成。")

    def _process_single_item(self, raw_data):
        """处理单条情报的核心流程"""
        # 0. 去重检查 (新增)
        news_url = raw_data.get('url')
        news_content = raw_data.get('content')
        news_summary = raw_data.get('summary')
        
        # 1.5 获取市场上下文与历史置信度 (Dimension A-C)
        context_str = self._enrich_market_context(raw_data)
        
        # 简单提取关键词作为上下文回测搜索
        keyword = "Trump" 
        if "Fed" in raw_data.get('content', ''): keyword = "Fed"
        
        stats = self.backtester.get_confidence_stats(keyword)
        if stats:
            bt_str = f"\n[历史回测面板]: 过去 {stats['count']} 次相关事件中 (关键词:{keyword})，黄金上涨概率 {stats['win_rate']}%, 平均波幅 {stats['avg_return']}%." 
            raw_data['content'] += bt_str
            context_str += bt_str

        # 1. 语义去重 (SimHash + BERT)
        # 提前检查，若语义重复，直接丢弃且不入库
        full_text = news_summary if (news_summary and len(str(news_summary)) > 20) else news_content
        
        # 此时还没有入库 ID，record_id 传 None (仅做内存记录)
        if self.deduplicator.is_duplicate(full_text, record_id=None):
            logger.info(f"🚫 发现语义重复情报 (BERT级别)，直接丢弃: {raw_data.get('title') or news_content[:50]}...")
            return

        # 2. 保存原始情报入库 (Save Raw)
        # 这将返回 ID，如果因 URL/SourceID 冲突返回 None，则为重复
        # 注意: save_raw_intelligence 使用 raw_data['content']
        db_id = self.db.save_raw_intelligence(raw_data)
        if not db_id:
            logger.info(f"🚫 发现重复情报 (SourceID冲突)，已存在，跳过: URL: {news_url}")
            return

        # 3. AI 分析
        analysis_result = None
        try:
            logger.info(f"正在分析情报: {raw_data.get('source')} - {raw_data.get('id')}")
            analysis_result = self.primary_llm.analyze(raw_data)
        except Exception:
            logger.warning("首选模型失败，尝试备用模型...")
            try:
                analysis_result = self.fallback_llm.analyze(raw_data)
            except Exception:
                logger.error(f"AI 分析失败，跳过: {raw_data.get('id')}")
                return

        if not analysis_result:
            return

        # 4. 结果更新与存储 (Update Analysis)
        # 去掉注入的上下文，保持纯净 (raw_data已在 save_raw 时使用了 dirty content? 
        # save_raw 使用了 raw_data['content']。
        # 这里我们需要 clean content 吗? 
        # engine.py 150 original logic: saved clean_content.
        # save_raw saved raw_data['content'] which includes bt_str context.
        # Ideally we should strictly save original content.
        # But 'raw_data' passed to save_raw had bt_str appended.
        # To fix this, we should clean raw_data['content'] AFTER analysis, or before save_raw passing a copy?
        # Simpler: remove context_str from raw_data['content'] before save_raw?
        # But we need context for AI analysis.
        # It's fine if Raw Data in DB has context string appended, it shows what AI saw.
        # User might prefer clean. 
        # Let's clean it for 'original_content' field usage in save_raw if possible.
        # raw_data['original_content'] is usually not set yet.
        
        clean_content = raw_data.get('content').replace(context_str, "")
        analysis_result['original_content'] = clean_content
        analysis_result['url'] = raw_data.get('url')
        
        # Update existing record
        self.db.update_intelligence_analysis(raw_data.get('id'), analysis_result, raw_data)

        # Apply Intraday Directional Deduplication
        signal_direction = self._parse_sentiment(analysis_result.get('sentiment'))
        if signal_direction in ['Long', 'Short']:
            trade_initiated = self.backtester.process_signal(signal_direction)
            if trade_initiated:
                logger.info(f"✅ 触发交易信号: {signal_direction} (来自 intelligence ID: {raw_data.get('id')})")
            else:
                logger.info(f"ℹ️ 未触发交易: 信号 {signal_direction} 被日内同向去重跳过 (来自 intelligence ID: {raw_data.get('id')})")

        # 4. 多渠道分发
        self._dispatch(analysis_result)

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
        # 同时也临时存入 raw_data 方便数据库保存时复用
        raw_data['dxy_snapshot'] = dxy
        raw_data['gvz_snapshot'] = gvz
        raw_data['fed_val'] = fed['value'] if fed else 0
        
        return context

    def _dispatch(self, data):
        title = f"【AlphaSignal】{data.get('sentiment', '情报警报')}"
        body = self._format_message(data)
        
        for channel in self.channels:
            channel.send(title, body)

    def _parse_sentiment(self, sentiment_json) -> str:
        """
        根据情绪文本确定交易方向。
        Returns: 'Long', 'Short', or 'Neutral'
        """
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
        # 格式化市场影响部分
        market_impact_str = ""
        market_implication = data.get('market_implication', {})
        
        if isinstance(market_implication, dict):
            for asset, impact in market_implication.items():
                market_impact_str += f"🔹 {asset}: {impact}\n"
        else:
            market_impact_str = str(market_implication)

        return f"""
🚨 【AlphaSignal 投资快报】
--------------------------------------------
📌 [核心摘要]
{data.get('summary')}

📊 [市场深度影响]
{market_impact_str.strip()}

💡 [实战策略建议]
{data.get('actionable_advice')}

🔗 [原文来源及链接]
{data.get('url')}
--------------------------------------------
(此消息由 AlphaSignal AI 实时生成，仅供参考)
"""