import json
from openai import OpenAI
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.llm.base import BaseLLM

class DeepSeekLLM(BaseLLM):
    async def analyze_async(self, raw_data):
        """异步版本的分析方法"""
        import asyncio
        return await asyncio.to_thread(self.analyze, raw_data)

    def analyze(self, raw_data):
        try:
            client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY, 
                base_url=settings.DEEPSEEK_BASE_URL
            )
            
            prompt = self._get_prompt(raw_data)
            
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            return json.loads(response.choices[0].message.content)
            
        except Exception as e:
            logger.error(f"DeepSeek 分析失败: {e}")
            raise e

    def analyze_batch(self, news_items):
        """批量分析（与 Gemini 保持一致的接口）"""
        try:
            client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY, 
                base_url=settings.DEEPSEEK_BASE_URL
            )
            
            # 使用与 Gemini 相同的批量 prompt
            from src.alphasignal.providers.llm.gemini import GeminiLLM
            prompt = GeminiLLM()._get_batch_prompt(news_items)
            
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            
            results = json.loads(response.choices[0].message.content)
            
            if len(results) != len(news_items):
                logger.warning(f"批量分析返回数量不匹配: 期望 {len(news_items)}, 实际 {len(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"DeepSeek 批量分析失败: {e}")
            raise e


    def _get_prompt(self, raw_data):
        return f"""
你是一个华尔街顶级宏观策略分析师。请分析以下内容并提取投资信号。
分析目标：识别该事件对【黄金 (Gold/XAU)】及相关市场的影响。

输入信息：
- 来源: {raw_data.get('source')}
- 作者: {raw_data.get('author')}
- 内容: {raw_data.get('content')}

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
    "urgency_score": 1-10 (整数，10为极度重要),
    "market_implication": {{
        "zh": "对市场影响的简要中文分析，重点放在黄金、美元、美债。",
        "en": "Brief analysis of market impact in English."
    }},
    "actionable_advice": {{
        "zh": "针对黄金交易员的具体中文操作建议（如：做多/做空/观望/对冲）。",
        "en": "Specific actionable advice for Gold traders in English."
    }}
}}
"""
