import asyncio
from typing import Any

from src.lucidpanda.core.logger import logger
from src.lucidpanda.prompts.delta_check_v1 import build_delta_check_prompt
from src.lucidpanda.prompts.refold_v1 import build_refold_prompt


class FollowerProcessor:
    """
    负责聚类中的 Follower 数据处理。
    负责增量检查 (Delta Check) 和 故事线演化 (Refold)。
    """

    def __init__(self, db, primary_llm, ai_semaphore):
        self.db = db
        self.primary_llm = primary_llm
        self.ai_semaphore = ai_semaphore

    async def process_follower_item_async(self, raw_data: dict[str, Any]):
        """处理聚类中的 Follower 数据，执行 Delta Check 和 Refold。"""
        source_id = raw_data.get("source_id") or raw_data.get("id")
        lead_id = raw_data.get("parent_lead_id")
        story_id = raw_data.get("parent_story_id")
        raw_content = raw_data.get("content")
        content = raw_content if isinstance(raw_content, str) else str(raw_content or "")

        if not lead_id:
            logger.warning(f"⚠️ Follower {source_id} missing parent_lead_id.")
            return

        async with self.ai_semaphore:
            try:
                # 提取 Lead 的 summary 作为 Delta Check 的基准
                lead_analysis = await asyncio.to_thread(
                    self.db.get_intelligence_analysis, lead_id
                )
                if not lead_analysis or not lead_analysis.get("summary"):
                    logger.warning(
                        f"⚠️ Lead {lead_id} 的分析结果尚未就绪，跳过 Follower {source_id} 的增量检查。"
                    )
                    return

                lead_summary_text = lead_analysis.get("summary")
                if isinstance(lead_summary_text, dict):
                    lead_summary_text = lead_summary_text.get(
                        "zh", str(lead_summary_text)
                    )
                elif isinstance(lead_summary_text, str):
                    pass
                else:
                    lead_summary_text = str(lead_summary_text)

                logger.info(
                    f"⚖️ 判断 Follower ({source_id}) 对 Lead ({lead_id}) 是否有信息增量 (Story Threading)..."
                )
                has_delta = await self._check_delta_gain(content, lead_summary_text)

                if not has_delta:
                    logger.info(f"🚫 无信息增量 (Follower): {source_id}")
                    await asyncio.to_thread(
                        self.db.update_intelligence_status,
                        source_id,
                        "CLUSTERED",
                        f"No Delta from Lead {lead_id}",
                    )
                else:
                    logger.info(f"🌟 发现重要增量 (Follower): {source_id}")
                    await self._refold_lead_summary(lead_id, content, story_id=story_id)
                    await asyncio.to_thread(
                        self.db.update_intelligence_status,
                        source_id,
                        "COMPLETED",
                        f"Delta Refolded to {lead_id}",
                    )
            except Exception as e:
                logger.error(f"处理 Follower 条目失败 {source_id}: {e}")
                await asyncio.to_thread(
                    self.db.update_intelligence_status,
                    source_id,
                    "FAILED",
                    f"Delta check error: {e}",
                )

    async def _check_delta_gain(self, new_content: str, lead_summary: str) -> bool:
        """使用 LLM 判定两个高度相似的文本之间是否存在“信息增量”。"""
        if not lead_summary or not new_content:
            return True

        prompt = build_delta_check_prompt(new_content, lead_summary)
        try:
            res = await self.primary_llm.generate_json_async(prompt, temperature=0.0)
            has_delta = bool(res.get("has_delta", False))
            if has_delta:
                logger.info(
                    f"✨ Delta Found: {res.get('reason')} | New Fact: {res.get('new_fact')}"
                )
            return has_delta
        except Exception as e:
            logger.warning(
                f"Delta Analysis failed, defaulting to True (Safety first): {e}"
            )
            return True

    async def _refold_lead_summary(
        self, lead_id: str, new_content: str, story_id: str | None = None
    ):
        """故事线演化：将新发现的增量事实融合进主事件（Lead）的摘要中。"""
        try:
            if story_id:
                logger.info(f"🔁 Refold Lead {lead_id} under story_id={story_id}")
            lead_analysis = await asyncio.to_thread(
                self.db.get_intelligence_analysis, lead_id
            )
            if not lead_analysis:
                logger.warning(f"Refold aborted: Lead {lead_id} analysis not found.")
                return

            summary = lead_analysis.get("summary", "")
            if isinstance(summary, dict):
                current_summary_zh = str(summary.get("zh", ""))
            else:
                current_summary_zh = str(summary or "")

            market_implication = lead_analysis.get("market_implication", "")
            if isinstance(market_implication, dict):
                current_market_implication_zh = str(
                    market_implication.get("zh", "")
                )
            else:
                current_market_implication_zh = str(market_implication or "")

            prompt = build_refold_prompt(
                current_summary_zh,
                current_market_implication_zh,
                new_content,
            )
            updated_analysis = await self.primary_llm.generate_json_async(
                prompt, temperature=0.2
            )

            if not updated_analysis or "summary" not in updated_analysis:
                logger.warning(f"Refold LLM output invalid for Lead {lead_id}")
                return

            lead_analysis.update(
                {
                    "summary": updated_analysis.get(
                        "summary", lead_analysis.get("summary")
                    ),
                    "sentiment": updated_analysis.get(
                        "sentiment", lead_analysis.get("sentiment")
                    ),
                    "sentiment_score": updated_analysis.get(
                        "sentiment_score", lead_analysis.get("sentiment_score")
                    ),
                    "urgency_score": updated_analysis.get(
                        "urgency_score", lead_analysis.get("urgency_score")
                    ),
                    "market_implication": updated_analysis.get(
                        "market_implication", lead_analysis.get("market_implication")
                    ),
                }
            )

            await asyncio.to_thread(
                self.db.update_lead_analysis, lead_id, lead_analysis
            )
            logger.info(f"🔄 故事线 Lead {lead_id} 摘要已通过 Refold 进化完成。")
        except Exception as e:
            logger.error(f"Refold 融合失败 for Lead {lead_id}: {e}")
