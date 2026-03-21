import json
from openai import OpenAI
from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger
from src.lucidpanda.providers.llm.base import BaseLLM

# 内容截断上限：RSS 摘要的黄金信号在前 800 字内就已完整包含
CONTENT_MAX_CHARS = 800
BATCH_CONTENT_CHARS = 400


class QwenLLM(BaseLLM):
    """
    阿里云百炼 Qwen LLM 实现
    使用 OpenAI 兼容协议（阿里云 DashScope 支持）
    """
    
    async def analyze_async(self, raw_data):
        """异步版本的分析方法"""
        import asyncio
        return await asyncio.to_thread(self.analyze, raw_data)

    async def generate_json_async(self, prompt: str, temperature: float = 0.2):
        """异步生成 JSON"""
        import asyncio
        return await asyncio.to_thread(self.generate_json, prompt, temperature)

    def analyze(self, raw_data):
        """单条新闻分析"""
        import time
        try:
            client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL
            )

            prompt = self._get_prompt(raw_data)
            
            logger.info(f"📤 [Qwen] 发起请求 -> Model: {settings.QWEN_MODEL}")
            logger.debug(f"📤 [Qwen] Prompt 预览：{prompt[:300]}...")

            start_time = time.time()
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=2000
            )
            elapsed = time.time() - start_time

            raw_text = response.choices[0].message.content
            logger.info(f"📥 [Qwen] 响应成功 (耗时：{elapsed:.2f}s)。原始输出摘录：{raw_text[:200]}...")

            return json.loads(raw_text)

        except Exception as e:
            logger.error(f"Qwen 分析失败：{e}")
            raise e

    def generate_json(self, prompt: str, temperature: float = 0.2):
        """通用 JSON 生成"""
        try:
            client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL
            )
            
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=temperature,
                max_tokens=2000
            )
            
            raw_text = response.choices[0].message.content
            return json.loads(raw_text)
            
        except Exception as e:
            logger.error(f"Qwen JSON 生成失败：{e}")
            raise e

    def analyze_batch(self, news_items):
        """批量分析"""
        import time
        try:
            client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL
            )

            prompt = self._get_batch_prompt(news_items)
            
            logger.info(f"📤 [Qwen] 批量分析 {len(news_items)} 条新闻")
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=4000
            )
            elapsed = time.time() - start_time

            raw_text = response.choices[0].message.content
            logger.info(f"📥 [Qwen] 批量响应成功 (耗时：{elapsed:.2f}s)")

            results = json.loads(raw_text)
            
            # 如果是数组格式，返回数组；如果是对象格式，提取 results 字段
            if isinstance(results, list):
                return results
            elif isinstance(results, dict) and 'results' in results:
                return results['results']
            else:
                logger.warning(f"Qwen 批量分析返回格式异常：{type(results)}")
                return [results]

        except Exception as e:
            logger.error(f"Qwen 批量分析失败：{e}")
            raise e

    def _truncate_content(self, text: str, max_chars: int) -> str:
        """截断过长内容，保留最有价值的头部信息。"""
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "...（已截断）"

    def _get_batch_prompt(self, news_items):
        """批量分析 Prompt"""
        news_list_str = ""
        for i, item in enumerate(news_items, 1):
            content = self._truncate_content(item.get('content', ''), BATCH_CONTENT_CHARS)
            news_list_str += f"""
[新闻 {i}]
- ID: {item.get('id')}
- 内容：{content}
- 市场背景：{item.get('context', '无')}
---
"""
        return f"""
你是一个华尔街顶级宏观策略分析师。请批量分析以下 {len(news_items)} 条新闻。
分析目标：识别对【黄金 (Gold/XAU)】及相关市场的影响。

输入：
{news_list_str}

输出格式要求：请必须输出标准的 JSON 数组格式，不要包含 Markdown 代码块标记。

JSON 数组，每个对象包含：
{{
    "news_id": "对应输入 ID",
    "summary": {{
        "zh": "50 字以内的中文简练摘要，突出核心事实。",
        "en": "Concise summary in English within 40 words."
    }},
    "sentiment": {{
        "zh": "情绪标签（鹰派/鸽派/避险/中性/利好/利空）",
        "en": "Sentiment Label (Hawkish/Dovish/Risk-off/Neutral/Bullish/Bearish)"
    }},
    "sentiment_score": -1.0 to 1.0,
    "urgency_score": 1-10 (整数),
    "market_implication": {{
        "zh": "结合当前背景的中文深评，重点放在黄金、美元、美债。",
        "en": "Deep analysis of market impact in English."
    }},
    "actionable_advice": {{
        "zh": "针对黄金交易员的具体中文操作建议。",
        "en": "Specific actionable advice for Gold traders in English."
    }},
    "entities": [
        {{
            "name": "实体名称",
            "type": "person/organization/policy/country/commodity/other",
            "impact": "bullish/bearish/neutral"
        }}
    ],
    "relations": [
        {{
            "from": "主体实体名",
            "to": "客体实体名",
            "relation": "关系类型",
            "direction": "forward/bidirectional",
            "strength": 0.0 to 1.0
        }}
    ]
}}

relations.relation 合法枚举：
- 利多黄金：raises_tariff, imposes_tariff, sanctions, geopolitical_risk, conflict_escalation, inflation_up, rate_cut_expectation, risk_off, usd_weakness, yield_down
- 利空黄金：rate_hike, usd_strength, real_yield_up, risk_on, disinflation

强约束：
1) 若新闻存在明确因果链，必须至少输出 1 条 relations。
2) relations 必须始终输出（无法提取时返回 []）。
"""

    def _get_prompt(self, raw_data):
        """单条分析 Prompt"""
        content = self._truncate_content(raw_data.get('content', ''), CONTENT_MAX_CHARS)
        return f"""
你是一个华尔街顶级宏观策略分析师。请分析以下内容并提取投资信号。
分析目标：识别该事件对【黄金 (Gold/XAU)】及相关市场的影响。

输入信息：
- 来源：{raw_data.get('source')}
- 作者：{raw_data.get('author')}
- 内容：{content}
- 市场背景：{raw_data.get('context', '无')}

输出格式要求：请必须输出标准的 JSON 格式，不要包含 Markdown 代码块标记。

JSON 结构定义：
{{
    "summary": {{
        "zh": "50 字以内的中文简练摘要，突出核心事实。",
        "en": "Concise summary in English within 40 words."
    }},
    "sentiment": {{
        "zh": "情绪标签（鹰派/鸽派/避险/中性/利好/利空）",
        "en": "Sentiment Label (Hawkish/Dovish/Risk-off/Neutral/Bullish/Bearish)"
    }},
    "sentiment_score": -1.0 to 1.0,
    "urgency_score": 1-10 (整数),
    "market_implication": {{
        "zh": "结合当前背景的中文深评，重点放在黄金、美元、美债。",
        "en": "Deep analysis of market impact in English."
    }},
    "actionable_advice": {{
        "zh": "针对黄金交易员的具体中文操作建议。",
        "en": "Specific actionable advice for Gold traders in English."
    }},
    "entities": [
        {{
            "name": "实体名称",
            "type": "person/organization/policy/country/commodity/other",
            "impact": "bullish/bearish/neutral"
        }}
    ],
    "relations": [
        {{
            "from": "主体实体名",
            "to": "客体实体名",
            "relation": "关系类型",
            "direction": "forward/bidirectional",
            "strength": 0.0 to 1.0
        }}
    ]
}}

relations.relation 合法枚举：
- 利多黄金：raises_tariff, imposes_tariff, sanctions, geopolitical_risk, conflict_escalation, inflation_up, rate_cut_expectation, risk_off, usd_weakness, yield_down
- 利空黄金：rate_hike, usd_strength, real_yield_up, risk_on, disinflation

强约束：
1) 若新闻存在明确因果链，必须至少输出 1 条 relations。
2) relations 必须始终输出（无法提取时返回 []）。
"""
