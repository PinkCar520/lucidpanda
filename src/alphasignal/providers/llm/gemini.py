import json
from google import genai
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.llm.base import BaseLLM

class GeminiLLM(BaseLLM):
    async def analyze_async(self, raw_data):
        """异步版本的分析方法"""
        import asyncio
        return await asyncio.to_thread(self.analyze, raw_data)

    def analyze(self, raw_data):
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            config = {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }
            
            prompt = self._get_prompt(raw_data)
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            res = json.loads(clean_text)
            logger.debug(f"🤖 AI Raw Analysis (Single): {json.dumps(res, ensure_ascii=False)[:200]}...")
            return res
            
        except Exception as e:
            logger.error(f"Gemini 分析失败: {e}")
            raise e

    def analyze_batch(self, news_items):
        try:
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            config = {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }
            
            prompt = self._get_batch_prompt(news_items)
            
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            
            clean_text = response.text.replace("```json", "").replace("```", "").strip()
            results = json.loads(clean_text)
            
            if len(results) != len(news_items):
                logger.warning(f"批量分析返回数量不匹配: 期望 {len(news_items)}, 实际 {len(results)}")
            
            logger.debug(f"🤖 AI Raw Analysis (Batch): Got {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Gemini 批量分析失败: {e}")
            raise e

    def _get_batch_prompt(self, news_items):
        news_list_str = ""
        for i, item in enumerate(news_items, 1):
            news_list_str += f"""
[新闻 {i}]
- ID: {item.get('id')}
- 内容: {item.get('content')}
- 市场背景: {item.get('context', '无')}
---
"""
        return f"""
你是一个华尔街顶级宏观策略分析师。请批量分析以下 {len(news_items)} 条新闻。
分析目标：识别对【黄金 (Gold/XAU)】及相关市场的影响。

输入：
{news_list_str}

输出格式要求：请必须输出标准的 JSON 数组格式，不要包含 Markdown 代码块标记（如 ```json）。

JSON 数组，每个对象包含：
{{
    "news_id": "对应输入 ID",
    "summary": {{
        "zh": "50字以内的中文简练摘要，突出核心事实。",
        "en": "Concise summary in English within 40 words."
    }},
    "sentiment": {{
        "zh": "情绪标签（鹰派/鸽派/避险/中性/利好/利空）",
        "en": "Sentiment Label (Hawkish/Dovish/Risk-off/Neutral/Bullish/Bearish)"
    }},
    "sentiment_score": -1.0 to 1.0 (数值，-1为极度利空黄金，1为极度利好黄金),
    "urgency_score": 1-10 (整数，10为极度重要),
    "market_implication": {{
        "zh": "结合当前背景（美元、波动、持仓、宏观）的中文深评，重点放在黄金、美元、美债。",
        "en": "Deep analysis of market impact in English."
    }},
    "actionable_advice": {{
        "zh": "针对黄金交易员的具体中文操作建议。注意：若持仓拥挤或波动剧烈，需体现风险规避。",
        "en": "Specific actionable advice for Gold traders in English."
    }}
}}
"""

    def _get_prompt(self, raw_data):
        return f"""
你是一个华尔街顶级宏观策略分析师。请分析以下内容并提取投资信号。
分析目标：识别该事件对【黄金 (Gold/XAU)】及相关市场的影响。

输入信息：
- 来源: {raw_data.get('source')}
- 作者: {raw_data.get('author')}
- 内容: {raw_data.get('content')}
- 市场背景: {raw_data.get('context', '无')}

输出格式要求：请必须输出标准的 JSON 格式，不要包含 Markdown 代码块标记（如 ```json）。

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
    "sentiment_score": -1.0 to 1.0 (数值，-1为极度利空黄金，1为极度利好黄金),
    "urgency_score": 1-10 (整数，10为极度重要),
    "market_implication": {{
        "zh": "结合当前背景（美元、波动、持仓、宏观）的中文深评，重点放在黄金、美元、美债。",
        "en": "Deep analysis of market impact in English."
    }},
    "actionable_advice": {{
        "zh": "针对黄金交易员的具体中文操作建议。注意：若持仓拥挤或波动剧烈，需体现风险规避。",
        "en": "Specific actionable advice for Gold traders in English."
    }}
}}
"""