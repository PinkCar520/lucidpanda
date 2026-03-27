"""
analysis_v1.py — 主分析 Agent Prompt
======================================
包含 LucidPanda AlphaEngine 的两个核心 Agent Prompt：
  1. build_agent_plan_prompt   — 规划是否调用工具
  2. build_agent_final_prompt  — 最终结构化分析输出

从 engine.py 提取并改进。关键改进点：
  - 实体提取铁律：强制要求 Person 级别实体必须提取
  - 提供别名候选提示（alias_hints），减少 LLM 乱造实体名的概率
"""

import json
from typing import Any

VERSION = "v1"

# ── 实体候选提示（来自 ontology.py CORE_ENTITIES 的别名摘要）──────────────
# 在 Prompt 内提供候选名单，提升实体归一化准确率
_ENTITY_HINT_EXAMPLES = [
    "鲍威尔 / Powell / Fed Chair → 美联储主席",
    "美联储 / FED / FOMC → 联邦储备委员会",
    "特朗普 / Trump / 川普 → 美国前总统",
    "中国人民银行 / 央行 / 人行 → PBOC",
    "黄金 / 金价 / XAU / 现货黄金 → Gold",
    "美元 / DXY / 美元指数 / 美指 → USD",
    "非农 / NFP / 美国非农就业 → US Nonfarm Payrolls",
    "CPI / 通胀数据 / 消费者物价指数 → US CPI",
]


def build_agent_plan_prompt(
    raw_data: dict[str, Any],
    tool_summaries: list[dict[str, Any]],
    max_tool_calls: int = 3,
) -> str:
    """
    构建 Agent 规划 Prompt（决定是否调用工具）。

    Args:
        raw_data: 原始情报数据字典
        tool_summaries: 可用工具摘要列表（ToolSpec 的 list_tool_summaries() 输出）
        max_tool_calls: 最大工具调用数

    Returns:
        str: Prompt 字符串
    """
    tool_list = json.dumps(tool_summaries, ensure_ascii=False)
    content = raw_data.get("content", "")
    context = raw_data.get("context", "无")

    return f"""你是 LucidPanda 的研究型 Agent。你的首要任务是分析宏观新闻对黄金市场的影响。
你可以选择性地使用以下工具来核验宏观数据，但不是必须的。

工具清单（JSON）:
{tool_list}

输入信息：
- 来源: {raw_data.get("source")}
- 作者: {raw_data.get("author")}
- 内容: {content[:1200]}
- 市场背景: {context}

输出要求：仅输出 JSON，不要包含 Markdown 代码块。
JSON 结构：
{{
  "use_tools": true/false,
  "plan_summary": "一句话说明是否需要工具与原因",
  "tool_calls": [
    {{
      "name": "tool_name",
      "args": {{"param": "value"}},
      "purpose": "一句话说明用途"
    }}
  ]
}}
约束：
1) 不需要工具时，tool_calls 必须为 []。
2) tool_calls 最多 {max_tool_calls} 个。
"""


def build_agent_final_prompt(
    raw_data: dict[str, Any],
    tool_results: list[dict[str, Any]],
    plan_response: dict[str, Any] | None,
    taxonomy: dict[str, list[str]] | None = None,
    macro_context: dict[str, Any] | None = None,
) -> str:
    """
    构建 Agent 最终分析 Prompt（输出结构化 JSON）。

    关键改进（vs 原 engine.py 内嵌版本）：
    - 新增"实体提取铁律"章节，强制区分 Person 和 Organization
    - 提供别名候选示例，减少实体名称碎片化
    - relations.relation 枚举更紧凑
    - 新增核心宏观指标（FRED）输入支持

    Args:
        raw_data: 原始情报数据字典
        tool_results: 工具调用结果列表
        plan_response: 规划阶段的 LLM 响应（提取 plan_summary）
        taxonomy: 动态分类体系字典
        macro_context: 美联储 FRED 核心宏观指标数据
    """
    content = raw_data.get("content", "")
    context = raw_data.get("context", "无")
    tools_json = json.dumps(tool_results, ensure_ascii=False)

    # 格式化宏观背景
    macro_info = "无"
    if macro_context:
        macro_info = "\n".join(
            [
                f"  - {v['name']} ({k}): {v['value']} (发布日期: {v['date']})"
                for k, v in macro_context.items()
                if v
            ]
        )

    plan_summary = ""
    if isinstance(plan_response, dict):
        plan_summary = plan_response.get("plan_summary") or ""

    # 注入 Taxonomy
    if not taxonomy:
        from src.lucidpanda.core.ontology import TAXONOMY

        taxonomy = TAXONOMY
    taxonomy_info = (
        f"多维分类标签 Taxonomy 参考 (仅可选以下值):\n"
        f"{json.dumps(taxonomy, ensure_ascii=False, indent=2)}"
    )

    # 实体候选提示
    alias_hints = "\n".join(f"  - {h}" for h in _ENTITY_HINT_EXAMPLES)

    return f"""你是一个华尔街顶级宏观策略分析师。请结合工具结果给出最终分析。
分析目标：识别该事件对【黄金 (Gold/XAU)】及相关市场的影响。

输入信息：
- 来源: {raw_data.get("source")}
- 作者: {raw_data.get("author")}
- 核心宏观背景 (FRED):
{macro_info}
- 内容: {content[:1200]}
- 市场背景: {context}
- 工具调用摘要: {plan_summary}
- 工具结果(JSON): {tools_json}

━━━ 实体提取铁律（必须遵守）━━━
1. 【人物必须拆分提取】：若新闻提及具体人物，必须单独提取为 type=person 的实体。
   例：新闻提到"鲍威尔讲话"→ 必须额外提取 name="鲍威尔", type="person"。
   不能只提取"美联储"而遗漏"鲍威尔"。
2. 【机构与资产也必须提取】：美联储/黄金/美债等核心资产必须出现在 entities 中。
3. 【使用以下别名参考对齐名称】（尽量使用标准化名称）：
{alias_hints}
4. 每个实体必须评估 impact（bullish/bearish/neutral），这是强制项。
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

输出格式要求：请必须输出标准的 JSON 格式，不要包含 Markdown 代码块标记。
JSON 结构定义：
{{
    "summary": {{
        "zh": "50字以内的中文简练摘要，突出核心事实。",
        "en": "Concise summary in English within 40 words."
    }},
    "sentiment": {{
        "zh": "情绪标签（鹰派/鸽派/避险/中性/利好/利空）",
        "en": "Sentiment Label (Hawkish/Dovish/Risk-off/Neutral/Bullish/Bearish)"
    }},
    "sentiment_score": -1.0 to 1.0,
    "urgency_score": 1-10,
    "market_implication": {{
        "zh": "结合当前背景（美元、波动、持仓、宏观）的中文深评，重点放在黄金、美元、美债。",
        "en": "Deep analysis of market impact in English."
    }},
    "actionable_advice": {{
        "zh": "针对黄金交易员的具体中文操作建议。注意：对反向波动需有风险规避方案。",
        "en": "Specific actionable advice for Gold traders in English."
    }},
    "entities": [
        {{
            "name": "实体名称（尽量使用标准化别名）",
            "type": "person/organization/policy/country/commodity/other",
            "impact": "bullish/bearish/neutral"
        }}
    ],
    "relations": [
        {{
            "from": "主体实体名",
            "to": "客体实体名",
            "relation": "关系类型（必须从枚举中选择）",
            "direction": "forward/bidirectional",
            "strength": 0.0 to 1.0
        }}
    ]
}}
{taxonomy_info}

relations.relation 合法枚举：
- 利多黄金：raises_tariff, imposes_tariff, sanctions, geopolitical_risk, conflict_escalation, inflation_up, rate_cut_expectation, risk_off, usd_weakness, yield_down
- 利空黄金：rate_hike, usd_strength, real_yield_up, risk_on, disinflation

强约束：
1) 若新闻存在明确因果链且涉及黄金驱动因子，必须至少输出 1 条 relations。
2) relations 必须始终输出（无法提取时返回 []，不可省略字段）。
3) entities 中 Person 类型不可遗漏（见铁律第1条）。
"""
