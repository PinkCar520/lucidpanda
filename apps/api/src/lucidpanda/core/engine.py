"""
Alpha Engine - AI 分析消费者
负责消费 intelligence 表中 status=PENDING 的记录进行 AI 分析
"""
import time
import json
import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import pytz
from src.lucidpanda.config import settings
from src.lucidpanda.config.llm_config import LLMConfigManager
from src.lucidpanda.core.logger import logger

# 引入组件
from src.lucidpanda.providers.llm.gemini import GeminiLLM
from src.lucidpanda.providers.llm.deepseek import DeepSeekLLM
from src.lucidpanda.providers.llm.qwen_llm import QwenLLM
from src.lucidpanda.providers.channels.email import EmailChannel
from src.lucidpanda.providers.channels.bark import BarkChannel
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.backtest import BacktestEngine
from src.lucidpanda.core.deduplication import NewsDeduplicator
from src.lucidpanda.core.event_clusterer import EventClusterer
from src.lucidpanda.services.agent_tools import call_tool, list_tool_summaries

# Prompt 模块（版本化管理，不再内嵌于代码）
from src.lucidpanda.prompts.analysis_v1 import build_agent_plan_prompt, build_agent_final_prompt
from src.lucidpanda.prompts.delta_check_v1 import build_delta_check_prompt
from src.lucidpanda.prompts.refold_v1 import build_refold_prompt


class LLMFactory:
    """LLM 工厂类，根据提供商名称创建对应的 LLM 实例"""
    
    @staticmethod
    def create(provider_name: str):
        """根据提供商名称创建 LLM 实例"""
        provider_name = provider_name.lower()
        
        if provider_name == LLMConfigManager.GEMINI:
            return GeminiLLM()
        elif provider_name == LLMConfigManager.DEEPSEEK:
            return DeepSeekLLM()
        elif provider_name == LLMConfigManager.QWEN:
            return QwenLLM()
        else:
            raise ValueError(f"未知的 LLM 提供商：{provider_name}")
    
    @staticmethod
    def get_fallback_provider(primary: str) -> str:
        """
        获取备用提供商
        
        从配置读取降级顺序，返回第一个可用的备用提供商。
        
        Args:
            primary: 主力提供商名称
            
        Returns:
            备用提供商名称
            
        Note:
            降级顺序可在 .env.ai 中通过 LLM_FALLBACK_ORDER 配置
        """
        # 从配置读取降级顺序
        fallback_order = settings.LLM_FALLBACK_ORDER
        
        # 返回第一个可用的备用提供商
        for provider in fallback_order:
            if provider != primary:
                config = LLMConfigManager.get_active_llm(provider)
                if config.enabled:
                    return provider
        
        # 如果没有可用的备用，返回第一个
        return fallback_order[0] if fallback_order else "qwen"


from src.lucidpanda.core.di_container import EngineDependencies


class AlphaEngine:
    """
    AI 分析消费者。
    不再负责采集，只消费 intelligence 表中 status=PENDING 的记录。
    RSS 采集由独立的 RSSCollector（run_collector.py）负责。
    
    使用依赖注入容器管理所有依赖，实现：
    - 依赖解耦
    - 单元测试友好
    - 按需初始化（节省内存）
    """
    def __init__(self, deps: Optional[EngineDependencies] = None):
        """
        初始化 AlphaEngine
        
        Args:
            deps: 依赖容器（可选，默认自动创建）
            
        Example:
            # 使用默认依赖
            engine = AlphaEngine()
            
            # 使用自定义依赖（测试场景）
            deps = EngineDependencies(db=mock_db)
            engine = AlphaEngine(deps=deps)
        """
        # 使用依赖注入容器
        self.deps = deps or EngineDependencies()
        
        # 从依赖容器获取组件
        self.db = self.deps.db
        self.primary_llm = self.deps.primary_llm
        self.fallback_llm = self.deps.fallback_llm
        self.ai_semaphore = self.deps.ai_semaphore
        self.backtester = self.deps.backtester
        self.clusterer = self.deps.clusterer
        self.deduplicator = self.deps.deduplicator
        self.channels = self.deps.channels
        self.enable_agent_tools = self.deps.enable_agent_tools
        self.tool_summaries = self.deps.tool_summaries
        self.entity_resolver = self.deps.entity_resolver
        self.factor_service = self.deps.factor_service
        
        # 日志记录
        primary_provider = settings.AI_PROVIDER.lower()
        fallback_provider = LLMFactory.get_fallback_provider(primary_provider)
        logger.info(f"🧠 选用 API: {primary_provider.upper()} 作为主力 AI 引擎")
        logger.info(f"🔄 备用 API: {fallback_provider.upper()} 作为降级方案")
        logger.info(f"🔒 并发限制：{settings.LLM_CONCURRENCY_LIMIT}")
        
        self._round_snapshot = {}
        
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
        await asyncio.to_thread(self.db.refresh_relation_rule_stats)

        # 1. 获取所有待分析记录 (PENDING/FAILED)
        pending_records = await asyncio.to_thread(self.db.get_pending_intelligence, limit=50)

        if not pending_records:
            logger.info("无待分析情报，本轮结束。")
            return

        # 2. 市场快照已经由 Collector 注入在 PENDING 记录中，Worker 无需重复抓取
        # 移除了原有的 fetch_round_snapshot 冗余逻辑

        # 2.5 事件聚类：同一事件多信源 → 只保留 lead 进全量 AI 分析，follower 进入 Delta Queue
        lead_records, follower_records = await asyncio.to_thread(
            self.clusterer.cluster, pending_records
        )
        if follower_records:
            logger.info(f"🔗 聚类捕获 {len(follower_records)} 条 Follower 报道，本轮全量分析 {len(lead_records)} 条 Lead")

        # 3. AI 并发分析 Leads
        enriched_items = lead_records
        for item in enriched_items:
            item.setdefault('extraction_method', 'RSS_SUMMARY')

        logger.info(f"🚀 并行分析 Lead 中 (并发数: {settings.LLM_CONCURRENCY_LIMIT}, 任务数: {len(enriched_items)})...")
        tasks = [self._process_single_item_async(item) for item in enriched_items]
        await asyncio.gather(*tasks)
        
        # 4. AI 并发分析 Followers (仅做轻量 Delta 检查和 Refold)
        if follower_records:
            logger.info(f"🔄 启动 Follower 增量检查 (任务数: {len(follower_records)})...")
            follower_tasks = [self._process_follower_item_async(item) for item in follower_records]
            await asyncio.gather(*follower_tasks)

        logger.info("<<< 本轮分析完成。")

    async def _process_follower_item_async(self, raw_data):
        """处理聚类中的 Follower 数据，执行 Delta Check 和 Refold。"""
        source_id = raw_data.get('source_id') or raw_data.get('id')
        lead_id = raw_data.get('parent_lead_id')
        
        if not lead_id:
            logger.warning(f"⚠️ Follower {source_id} missing parent_lead_id.")
            return

        async with self.ai_semaphore:
            try:
                # 提取 Lead 的 summary 作为 Delta Check 的基准
                lead_analysis = await asyncio.to_thread(self.db.get_intelligence_analysis, lead_id)
                if not lead_analysis or not lead_analysis.get('summary'):
                    logger.warning(f"⚠️ Lead {lead_id} 的分析结果尚未就绪，跳过 Follower {source_id} 的增量检查。")
                    return
                
                lead_summary_text = lead_analysis.get('summary')
                if isinstance(lead_summary_text, dict):
                    lead_summary_text = lead_summary_text.get('zh', str(lead_summary_text))
                elif isinstance(lead_summary_text, str):
                    pass
                else:
                    lead_summary_text = str(lead_summary_text)

                logger.info(f"⚖️ 判断 Follower ({source_id}) 对 Lead ({lead_id}) 是否有信息增量 (Story Threading)...")
                has_delta = await self._check_delta_gain(raw_data.get('content'), lead_summary_text)
                
                if not has_delta:
                    logger.info(f"🚫 无信息增量 (Follower): {source_id}")
                    # 在 DB 中更新状态
                    await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'CLUSTERED', f"No Delta from Lead {lead_id}")
                else:
                    logger.info(f"🌟 发现重要增量 (Follower): {source_id}")
                    # 融合反转内容到 Lead，实现故事树折叠 (Refold)
                    await self._refold_lead_summary(lead_id, raw_data.get('content'))
                    # 更新自己的状态
                    await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'COMPLETED', f"Delta Refolded to {lead_id}")
            except Exception as e:
                logger.error(f"处理 Follower 条目失败 {source_id}: {e}")
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'FAILED', f"Delta check error: {e}")

    async def _process_single_item_async(self, raw_data):
        """单条情报的异步处理状态机"""
        source_id = raw_data.get('source_id') or raw_data.get('id')
        
        async with self.ai_semaphore:
            try:
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'PROCESSING')
                
                # 1. 注入上下文
                await asyncio.to_thread(self._enrich_market_context, raw_data)
                
                # 2. 早期极速查重 (仅 URL)
                dup_result = await asyncio.to_thread(
                    self.deduplicator.is_early_duplicate, 
                    raw_data.get('url')
                )
                
                # 情况 A: 确定性重复 (L1 拦截)
                if dup_result["is_duplicate"]:
                    lead_id_a = dup_result.get('lead_id')
                    logger.info(f"🚫 确定性重复 (URL拦截): {source_id} -> Lead ID: {lead_id_a}")
                    await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'COMPLETED', f"Duplicate of {lead_id_a}")
                    return

                # 将去重推后

                # 3. AI 分析
                logger.info(f"🤖 正在分析({raw_data.get('extraction_method', 'UNKNOWN')}): {source_id}")
                
                # 获取动态分类体系 (Taxonomy)
                taxonomy_dict = None
                if self.entity_resolver.registry_service:
                    taxonomy = self.entity_resolver.registry_service.get_taxonomy_config()
                    if taxonomy:
                        taxonomy_dict = {}
                        for row in taxonomy:
                            dim = row['dimension']
                            val = row['value']
                            if dim not in taxonomy_dict:
                                taxonomy_dict[dim] = []
                            taxonomy_dict[dim].append(val)

                try:
                    if self.enable_agent_tools:
                        analysis_result = await self._analyze_with_tools(self.primary_llm, raw_data, taxonomy=taxonomy_dict)
                    else:
                        analysis_result = await self.primary_llm.analyze_async(raw_data, taxonomy=taxonomy_dict)
                except Exception as e:
                    logger.warning(f"Primary LLM failed for {source_id}, trying fallback: {e}")
                    if self.enable_agent_tools:
                        analysis_result = await self._analyze_with_tools(self.fallback_llm, raw_data, taxonomy=taxonomy_dict)
                    else:
                        analysis_result = await self.fallback_llm.analyze_async(raw_data, taxonomy=taxonomy_dict)

                # 4. 存储分析结果 (必须包含 summary)
                if analysis_result and analysis_result.get("summary"):
                    # 4.1 实体链接对齐 (Entity Resolution)
                    if "entities" in analysis_result and isinstance(analysis_result["entities"], list):
                        raw_ai_entities = [e.get('name') for e in analysis_result["entities"] if e.get('name')]
                        logger.debug(f"🤖 Raw AI Entities: {raw_ai_entities}")
                        
                        analysis_result["entities"] = await asyncio.to_thread(self.entity_resolver.process_ai_entities, analysis_result["entities"])
                        
                        # 日志：展示解析后的实体
                        resolved_cids = [e.get('canonical_id') for e in analysis_result["entities"] if e.get('canonical_id')]
                        if resolved_cids:
                            logger.info(f"🧠 Resolved Entities: {resolved_cids}")
                        else:
                            logger.warning(f"⚠️ No entities resolved to canonical IDs for {source_id}")

                        # 新增：记录未匹配上的实体
                        missed_entities = [e.get("name") for e in analysis_result["entities"] if not e.get("canonical_id") and e.get("name")]
                        if missed_entities:
                            await asyncio.to_thread(self.db.log_entity_miss_batch, source_id, missed_entities)

                        # 4.2 触发舆情因子聚合 (Factor Indexing)
                        sentiment_score = analysis_result.get("sentiment_score", 0.0)
                        urgency_score = analysis_result.get("urgency_score", 1)
                        for ent in analysis_result["entities"]:
                            cid = ent.get("canonical_id")
                            if cid:
                                # 异动检测 (3-sigma Anomaly Alert)
                                anomaly_info = await self.factor_service.check_sentiment_anomaly(cid, sentiment_score)
                                if anomaly_info.get("is_anomaly"):
                                    logger.warning(f"🚨 因子异动告警! {cid} 情绪突破 3σ (Z-Score: {anomaly_info.get('z_score')}, 现值: {sentiment_score}, 均值: {anomaly_info.get('current_mean')})")
                                    bark = self.channels.get('bark')
                                    if bark:
                                        try:
                                            await bark.send_message_async(
                                                title=f"🚨 情绪异动警报: {ent.get('name', cid)}", 
                                                body=f"检测到突破 3σ 的显著情绪变化！\n当前情绪: {sentiment_score}\n历史均值: {anomaly_info.get('current_mean')}\n驱动事件: {analysis_result.get('summary', '')[:50]}...",
                                                group="LucidPanda_Factor"
                                            )
                                        except Exception as e:
                                            logger.error(f"发送 Bark 告警失败: {e}")

                                await self.factor_service.update_entity_factor_async(
                                    cid, 
                                    sentiment_score, 
                                    urgency_score
                                )

                    # 4.3 实体感知语义精筛 (Semantic Deduplication)
                    # 只有拿到实体和情绪了，才能精准防反转丢失
                    resolved_entities_cids = [e.get('canonical_id') for e in analysis_result["entities"] if e.get('canonical_id')]
                    
                    sem_dup = await asyncio.to_thread(
                        self.deduplicator.is_semantic_duplicate,
                        raw_data.get('content'),
                        entities=resolved_entities_cids,
                        sentiment=sentiment_score
                    )
                    
                    if sem_dup["is_duplicate"]:
                        logger.info(f"🚫 语义精筛命中 (拦截): {source_id} -> 重复于 Lead {sem_dup.get('lead_id')}")
                        await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'COMPLETED', f"Duplicate of {sem_dup.get('lead_id')}")
                        return
                    elif sem_dup["status"] == "SENTIMENT_REVERSAL":
                        logger.warning(f"🚨 发现反转新闻 (Sentiment Reversal 放行): {source_id} 与 Lead {sem_dup.get('lead_id')} 情绪完全向左！")
                        raw_data['is_story_update'] = True
                        raw_data['parent_lead_id'] = sem_dup.get('lead_id')
                    elif sem_dup["status"] == "SUSPECTED":
                        logger.info(f"⚖️ 发起疑似数据的后置 Delta 检测 ({source_id})")
                        has_delta = await self._check_delta_gain(raw_data.get('content'), sem_dup.get("lead_summary"))
                        if not has_delta:
                            logger.info(f"🚫 无信息增量 (拦截): {source_id} -> 相似于 Lead {sem_dup.get('lead_id')}")
                            await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'COMPLETED', f"No Delta from {sem_dup.get('lead_id')}")
                            return
                        else:
                            logger.info(f"🌟 发现重要增量 (放行): {source_id}")
                            raw_data['is_story_update'] = True
                            raw_data['parent_lead_id'] = sem_dup.get('lead_id')
                            asyncio.create_task(self._refold_lead_summary(sem_dup.get('lead_id'), raw_data.get('content')))

                    # 将最终的向量赋给分析结果
                    analysis_result['embedding'] = self.deduplicator.last_vector

                    if self.deduplicator.last_vector is not None:
                        await asyncio.to_thread(
                            self.db.save_embedding_vec, source_id, self.deduplicator.last_vector
                        )

                    await asyncio.to_thread(self.db.update_intelligence_analysis, source_id, analysis_result, raw_data)
                    await asyncio.to_thread(self.db.upsert_knowledge_graph, source_id, analysis_result)
                    await self._trigger_trade_and_dispatch(analysis_result, raw_data)
                else:
                    raise ValueError("AI analysis returned empty result or missing summary")
                
            except Exception as e:
                logger.error(f"处理条目失败 {source_id}: {e}")
                await asyncio.to_thread(self.db.update_intelligence_status, source_id, 'FAILED', str(e))

    async def _check_delta_gain(self, new_content: str, lead_summary: str) -> bool:
        """
        使用 LLM 判定两个高度相似的文本之间是否存在“信息增量”。
        """
        if not lead_summary or not new_content:
            return True
            
        prompt = f"""
你是一个专业的新闻编辑。请对比以下“已有内容摘要”和“新消息内容”，判定新消息是否包含任何“实质性的信息增量”。

【判定标准】：
1. 包含新发布的数据点（如：具体的伤亡数字更新、利率数值、价格变动等）。
2. 包含新的事态进展或反转（如：事件已从“传言”变为“证实”）。
3. 包含新的因果解释或重要评论。
※ 若仅为措辞微调、翻译差异或无意义的重复，请判定为无增量。

【输入】：
- 已有内容摘要: {lead_summary}
- 新消息内容: {new_content[:1000]} 

【输出格式】：
请直接返回 JSON 格式：
{{"has_delta": boolean, "reason": "简短原因", "new_fact": "提取的新事实（若有）"}}
"""
        try:
            # 优先使用 Flash 模型进行低成本快速判定
            res = await self.primary_llm.generate_json_async(prompt, temperature=0.0)
            has_delta = res.get("has_delta", False)
            if has_delta:
                logger.info(f"✨ Delta Found: {res.get('reason')} | New Fact: {res.get('new_fact')}")
            return has_delta
        except Exception as e:
            logger.warning(f"Delta Analysis failed, defaulting to True (Safety first): {e}")
            return True

    async def _refold_lead_summary(self, lead_id: str, new_content: str):
        """
        故事线演化：将新发现的增量事实融合进主事件（Lead）的摘要中。
        """
        try:
            # 1. 获取 Lead 的当前分析结果
            lead_analysis = await asyncio.to_thread(self.db.get_intelligence_analysis, lead_id)
            if not lead_analysis:
                logger.warning(f"Refold aborted: Lead {lead_id} analysis not found.")
                return

            # 2. 构建 Refold Prompt
            prompt = f"""
你是一个专业的新闻主编。请根据“新发现的事实”更新现有的“主事件综述”。

【现有综述】：
- 摘要: {(lead_analysis.get('summary') or {}).get('zh', "无")}
- 市场影响: {(lead_analysis.get('market_implication') or {}).get('zh', "无")}

【新发现的事实/内容】：
{new_content[:1500]}

【任务要求】：
1. 保持原有综述的核心内容不丢失。
2. 将新事实有机地融入摘要中，使其成为最新的“事件全貌”。
3. 如果情绪 (sentiment) 或紧迫性 (urgency_score) 发生显著变化，请相应调整。
4. 语言必须简洁、专业（分析师语气）。

【输出格式】：
请直接返回更新后的 JSON 格式分析结果（包含 summary, sentiment, sentiment_score, urgency_score, market_implication 结构）：
"""
            # 3. 调用 LLM 进行融合 (使用效率模型 Flash)
            updated_analysis = await self.primary_llm.generate_json_async(prompt, temperature=0.2)
            
            if not updated_analysis or "summary" not in updated_analysis:
                logger.warning(f"Refold LLM output invalid for Lead {lead_id}")
                return

            # 4. 合并感知字段并持久化
            # 我们主要更新摘要、情绪分值、紧迫性和市场影响
            lead_analysis.update({
                "summary": updated_analysis.get("summary", lead_analysis.get("summary")),
                "sentiment": updated_analysis.get("sentiment", lead_analysis.get("sentiment")),
                "sentiment_score": updated_analysis.get("sentiment_score", lead_analysis.get("sentiment_score")),
                "urgency_score": updated_analysis.get("urgency_score", lead_analysis.get("urgency_score")),
                "market_implication": updated_analysis.get("market_implication", lead_analysis.get("market_implication")),
            })
            
            await asyncio.to_thread(self.db.update_lead_analysis, lead_id, lead_analysis)
            logger.info(f"🔄 故事线 Lead {lead_id} 摘要已通过 Refold 进化完成。")
            
        except Exception as e:
            logger.error(f"Refold 融合失败 for Lead {lead_id}: {e}")


    async def _analyze_with_tools(self, llm, raw_data: Dict[str, Any], taxonomy: Optional[dict] = None) -> Dict[str, Any]:
        if not hasattr(llm, "generate_json_async") or not self.tool_summaries:
            return await llm.analyze_async(raw_data, taxonomy=taxonomy)

        plan_prompt = self._build_agent_plan_prompt(raw_data)
        try:
            plan_response = await llm.generate_json_async(plan_prompt, temperature=0.2)
        except Exception as exc:
            logger.warning(f"Agent planning failed, fallback to direct analysis: {exc}")
            return await llm.analyze_async(raw_data)

        tool_calls = self._extract_tool_calls(plan_response)
        tool_results: List[Dict[str, Any]] = []
        if tool_calls:
            tool_results = await self._run_tool_calls(tool_calls)

        final_prompt = self._build_agent_final_prompt(raw_data, tool_results, plan_response, taxonomy=taxonomy)
        try:
            analysis_result = await llm.generate_json_async(final_prompt, temperature=0.2)
        except Exception as exc:
            logger.warning(f"Agent final analysis failed, fallback to direct analysis: {exc}")
            return await llm.analyze_async(raw_data, taxonomy=taxonomy)

        agent_trace = {
            "version": 1,
            "plan_summary": (plan_response or {}).get("plan_summary"),
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "generated_at": datetime.utcnow().isoformat(),
        }
        if isinstance(analysis_result, dict):
            analysis_result.setdefault("agent_trace", agent_trace)
        return analysis_result

    def _extract_tool_calls(self, plan_response: Any) -> List[Dict[str, Any]]:
        if not isinstance(plan_response, dict):
            return []
        tool_calls = plan_response.get("tool_calls") or []
        if not isinstance(tool_calls, list):
            return []
        max_calls = max(1, int(getattr(settings, "AGENT_TOOL_MAX_CALLS", 3)))
        sanitized = []
        for call in tool_calls[:max_calls]:
            if not isinstance(call, dict):
                continue
            name = call.get("name")
            args = call.get("args") or {}
            if not name:
                continue
            if not isinstance(args, dict):
                args = {}
            sanitized.append({"name": name, "args": args, "purpose": call.get("purpose")})
        return sanitized

    async def _run_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        timeout = max(1, int(getattr(settings, "AGENT_TOOL_TIMEOUT_SECONDS", 8)))

        async def _call_one(call: Dict[str, Any]) -> Dict[str, Any]:
            try:
                result = await asyncio.wait_for(
                    asyncio.to_thread(call_tool, call.get("name"), call.get("args")),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                result = {"error": f"Tool {call.get('name')} timed out after {timeout}s"}
            return {
                "name": call.get("name"),
                "args": call.get("args"),
                "purpose": call.get("purpose"),
                "result": result,
            }

        tasks = [_call_one(call) for call in tool_calls]
        return await asyncio.gather(*tasks) if tasks else []

    def _build_agent_plan_prompt(self, raw_data: Dict[str, Any]) -> str:
        """委托 prompts/analysis_v1.py 构建 Agent 规划 Prompt。"""
        max_calls = max(1, int(getattr(settings, "AGENT_TOOL_MAX_CALLS", 3)))
        return build_agent_plan_prompt(raw_data, self.tool_summaries, max_tool_calls=max_calls)

    def _build_agent_final_prompt(
        self,
        raw_data: Dict[str, Any],
        tool_results: List[Dict[str, Any]],
        plan_response: Optional[Dict[str, Any]],
        taxonomy: Optional[dict] = None
    ) -> str:
        """委托 prompts/analysis_v1.py 构建 Agent 最终分析 Prompt（含实体提取铁律）。"""
        return build_agent_final_prompt(raw_data, tool_results, plan_response, taxonomy=taxonomy)

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
        from src.lucidpanda.utils.market_calendar import is_gold_market_open
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

        title = f"【LucidPanda】{sentiment_text}"
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
🚨 【LucidPanda 投资快报】
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
(此消息由 LucidPanda AI 实时生成，仅供参考)
"""
