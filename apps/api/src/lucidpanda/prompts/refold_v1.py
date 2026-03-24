"""
refold_v1.py — 故事线演化 (Refold) Prompt
==========================================
用于 LLM 将新发现的增量事实融合进 Lead 摘要，实现"事件综述进化"。
从 engine.py._refold_lead_summary() 提取并改进。
"""

VERSION = "v1"


def build_refold_prompt(
    current_summary_zh: str,
    current_market_implication_zh: str,
    new_content: str,
    max_new_content_chars: int = 1500,
) -> str:
    """
    构建 Refold（故事线演化）Prompt。

    Args:
        current_summary_zh: Lead 当前的中文摘要
        current_market_implication_zh: Lead 当前的中文市场影响分析
        new_content: 新内容（已通过 Delta 判定，确认包含增量）
        max_new_content_chars: 截断新内容的最大字符数

    Returns:
        str: 拼装好的 Prompt 字符串
    """
    truncated_content = new_content[:max_new_content_chars]

    return f"""你是一个专业的新闻主编。请根据"新发现的事实"更新现有的"主事件综述"。

【现有综述】：
- 摘要: {current_summary_zh or "无"}
- 市场影响: {current_market_implication_zh or "无"}

【新发现的事实/内容】（已确认包含增量，请认真融合）：
{truncated_content}

【任务要求】：
1. 保持原有综述的核心内容不丢失，只补充/修正，不删除关键信息。
2. 将新事实有机地融入摘要中，使其成为最新的"事件全貌"。
3. 如果情绪方向或紧迫性发生显著变化（如"传言"→"证实"会提升紧迫性），请相应调整。
4. 语言必须简洁、专业（分析师语气，中文）。

【输出格式】：
请直接返回 JSON（不要包含 markdown 代码块）：
{{
    "summary": {{"zh": "更新后的中文摘要（< 80字）", "en": "Updated English summary (< 60 words)"}},
    "sentiment": {{"zh": "情绪标签（鹰派/鸽派/避险/中性/利好/利空）", "en": "Sentiment Label"}},
    "sentiment_score": -1.0 to 1.0,
    "urgency_score": 1-10,
    "market_implication": {{"zh": "更新后的中文市场影响（< 100字）", "en": "Updated English market impact"}}
}}"""
