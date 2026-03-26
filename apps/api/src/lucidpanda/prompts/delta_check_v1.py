"""
delta_check_v1.py — Delta 信息增量判定 Prompt
=============================================
用于 LLM 判断一条新报道相对于已有 Lead 摘要是否包含实质性增量。
从 engine.py._check_delta_gain() 提取并改进。
"""

VERSION = "v1"


def build_delta_check_prompt(lead_summary:
    str, new_content: str, max_new_content_chars: int = 1000) -> str:
    """
    构建 Delta 判定 Prompt。

    Args:
        lead_summary: Lead 新闻的已有摘要（来自 DB）
        new_content: 新消息的完整内容
        max_new_content_chars: 截断新内容的最大字符数（防止超出 token 限制）

    Returns:
        str: 拼装好的 Prompt 字符串
    """
    truncated_content = new_content[:max_new_content_chars]

    return f"""你是一个专业的新闻编辑。请对比以下"已有内容摘要"和"新消息内容"，\
判定新消息是否包含任何"实质性的信息增量"。

【判定标准】：
1. 包含新发布的数据点（如：具体的伤亡数字更新、利率数值、价格变动等）。
2. 包含新的事态进展或反转（如：事件已从"传言"变为"证实"，或官方立场逆转）。
3. 包含新的因果解释或重要权威评论（如：央行主席新的表态）。
4. 包含时间锚点("今日""昨日")强调的最新事实。
※ 若仅为措辞微调、翻译差异、不同媒体的同质转载，请判定为无增量。

【输入】：
- 已有内容摘要: {lead_summary}
- 新消息内容: {truncated_content}

【输出格式】：
请直接返回 JSON 格式（不要包含 markdown 代码块）：
{{"has_delta": boolean, "reason": "简短原因（< 30字）", "new_fact": "提取的核心新事实（若无则留空）"}}"""
