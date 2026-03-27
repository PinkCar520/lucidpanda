import json
from typing import Any

from openai import OpenAI

from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger
from src.lucidpanda.core.ontology import TAXONOMY
from src.lucidpanda.providers.llm.base import BaseLLM

# 内容截断上限
CONTENT_MAX_CHARS = 800
BATCH_CONTENT_CHARS = 400

class QwenLLM(BaseLLM):
    """阿里云百炼 Qwen LLM 实现"""
    
    async def analyze_async(self, raw_data, taxonomy: dict | None = None):
        """异步版本的分析方法"""
        import asyncio
        return await asyncio.to_thread(self.analyze, raw_data, taxonomy)

    async def generate_json_async(self, prompt: str, temperature: float = 0.2):
        import asyncio
        return await asyncio.to_thread(self.generate_json, prompt, temperature)

    def analyze(self, raw_data, taxonomy: dict | None = None):
        import time
        try:
            client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL
            )

            prompt = self._get_prompt(raw_data, taxonomy)
            
            logger.info(f"📤 [Qwen] 发起请求 -> Model: {settings.QWEN_MODEL}")

            start_time = time.time()
            response = client.chat.completions.create(
                model=settings.QWEN_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=2000
            )
            elapsed = time.time() - start_time

            raw_text = response.choices[0].message.content
            logger.info(f"📥 [Qwen] 响应成功 (耗时：{elapsed:.2f}s)。")

            return self._parse_json(raw_text)

        except Exception as e:
            if 'raw_text' in locals() and raw_text == "":
                logger.error(f"Qwen 返回了空响应。请检查模型名称 '{settings.QWEN_MODEL}' 是否正确。")
            elif 'raw_text' in locals():
                logger.error(f"Qwen 返回了非 JSON 格式: {raw_text[:200]}...")
            logger.error(f"Qwen 分析失败：{e}")
            raise e

    def generate_json(self, prompt: str, temperature: float = 0.2):
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
            return self._parse_json(raw_text)
            
        except Exception as e:
            logger.error(f"Qwen JSON 生成失败：{e}")
            raise e

    def analyze_batch(self, news_items, taxonomy: dict | None = None):
        import time
        try:
            client = OpenAI(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL
            )

            prompt = self._get_batch_prompt(news_items, taxonomy)
            
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

            results = self._parse_json(raw_text)
            
            if isinstance(results, list):
                return results
            elif isinstance(results, dict) and 'results' in results:
                return results['results']
            else:
                return [results]

        except Exception as e:
            if 'raw_text' in locals() and raw_text == "":
                logger.error(f"Qwen 批量分析返回了空响应。请检查模型名称 '{settings.QWEN_MODEL}' 是否正确。")
            elif 'raw_text' in locals():
                logger.error(f"Qwen 批量分析返回了非 JSON 格式: {raw_text[:200]}...")
            logger.error(f"Qwen 批量分析失败：{e}")
            raise e

    def _truncate_content(self, text: str, max_chars: int) -> str:
        if not text:
            return ""
        text = text.strip()
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "...（已截断）"

    def _get_batch_prompt(self, news_items, taxonomy: dict | None = None):
        taxonomy_to_use = taxonomy or TAXONOMY
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
你是华尔街顶级宏观策略分析师。请批量分析 {len(news_items)} 条新闻。
目标：产出对【黄金 (Gold/XAU)】及相关市场的影响分析。

输入：
{news_list_str}

输出格式：标准 JSON 数组（不要包含 Markdown）。

数组中每个对象格式：
{{
    "news_id": "ID",
    "summary": {{"zh": "中文摘要", "en": "English summary"}},
    "sentiment": {{"zh": "鹰派/鸽派等", "en": "Hawkish/Dovish etc."}},
    "sentiment_score": -1.0 to 1.0,
    "urgency_score": 1-10,
    "market_implication": {{"zh": "中文深评", "en": "Deep analysis"}},
    "actionable_advice": {{"zh": "中文操作建议", "en": "Actionable advice"}},
    "entities": [{{"name": "实体名", "type": "类型", "impact": "影响"}}],
    "tags": [{{"dimension": "维度", "value": "标签值", "weight": 权重}}],
    "relations": [{{"from": "A", "to": "B", "relation": "R", "direction": "D", "strength": S}}]
}}

多维分类标签 Taxonomy 参考 (仅可选以下值):
{json.dumps(taxonomy_to_use, ensure_ascii=False, indent=2)}

relations.relation 枚举：
- 利多黄金：raises_tariff, imposes_tariff, sanctions, geopolitical_risk, conflict_escalation, inflation_up, rate_cut_expectation, risk_off, usd_weakness, yield_down
- 利空黄金：rate_hike, usd_strength, real_yield_up, risk_on, disinflation
"""

    def _get_prompt(self, raw_data, taxonomy: dict | None = None):
        taxonomy_to_use = taxonomy or TAXONOMY
        content = self._truncate_content(raw_data.get('content', ''), CONTENT_MAX_CHARS)
        return f"""
你是华尔街顶级宏观策略分析师。请分析以下内容。
目标：识别对【黄金 (Gold/XAU)】及相关市场的影响。

输入：
- 来源：{raw_data.get('source')}
- 作者：{raw_data.get('author')}
- 内容：{content}
- 市场背景：{raw_data.get('context', '无')}

输出格式：标准 JSON（不要包含 Markdown）。

JSON 结构：
{{
    "summary": {{"zh": "中文摘要", "en": "English summary"}},
    "sentiment": {{"zh": "情绪", "en": "Sentiment"}},
    "sentiment_score": -1.0 to 1.0,
    "urgency_score": 1-10,
    "market_implication": {{"zh": "中文深评", "en": "Deep analysis"}},
    "actionable_advice": {{"zh": "实战建议", "en": "Advice"}},
    "entities": [{{"name": "实体", "type": "类型", "impact": "影响"}}] ,
    "tags": [{{"dimension": "维度", "value": "值", "weight": 权重}}],
    "relations": [{{"from": "A", "to": "B", "relation": "R", "direction": "D", "strength": S}}]
}}

多维分类标签 Taxonomy 参考:
{json.dumps(taxonomy_to_use, ensure_ascii=False, indent=2)}

relations.relation 枚举：
- 利多黄金：raises_tariff, imposes_tariff, sanctions, geopolitical_risk, conflict_escalation, inflation_up, rate_cut_expectation, risk_off, usd_weakness, yield_down
- 利空黄金：rate_hike, usd_strength, real_yield_up, risk_on, disinflation
"""
    def _parse_json(self, text: str) -> Any:
        """从字符串中提取并解析 JSON，处理可能的 Markdown 代码块"""
        if not text:
            return {}
        text = text.strip()
        # 移除 Markdown 代码块标记回退
        if text.startswith("```"):
            import re
            match = re.search(r"```(?:json)?\s*(\{.*\}|\[.*\])\s*```", text, re.DOTALL)
            if match:
                text = match.group(1)
            else:
                # 尝试直接去掉前后的 ```
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # 最后的尝试：寻找第一个 { 和最后一个 }
            import re
            match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
            if match:
                return json.loads(match.group(1))
            raise
