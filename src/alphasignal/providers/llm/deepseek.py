import json
from openai import OpenAI
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.llm.base import BaseLLM

# 内容截断上限（同 Gemini）
CONTENT_MAX_CHARS = 800


class DeepSeekLLM(BaseLLM):
    async def analyze_async(self, raw_data):
        """异步版本的分析方法"""
        import asyncio
        return await asyncio.to_thread(self.analyze, raw_data)

    def analyze(self, raw_data):
        import time
        try:
            client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY, 
                base_url=settings.DEEPSEEK_BASE_URL
            )
            
            prompt = self._get_prompt(raw_data)
            
            logger.info(f"📤 [DeepSeek] 发起请求 -> Base: {settings.DEEPSEEK_BASE_URL} | Model: {settings.DEEPSEEK_MODEL}")
            logger.debug(f"📤 [DeepSeek] Prompt 预览: {prompt[:300]}...")
            
            start_time = time.time()
            response = client.chat.completions.create(
                model=settings.DEEPSEEK_MODEL,
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            elapsed = time.time() - start_time
            
            raw_text = response.choices[0].message.content
            logger.info(f"📥 [DeepSeek] 响应成功 (耗时: {elapsed:.2f}s)。原始输出摘录: {raw_text[:200]}...")
            
            return json.loads(raw_text)
            
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
        content = raw_data.get('content', '')
        if len(content) > CONTENT_MAX_CHARS:
            content = content[:CONTENT_MAX_CHARS] + "...（已截断）"
            
        return f"""
你是一个华尔街顶级宏观策略分析师。请分析以下内容并提取投资信号。
分析目标：识别该事件对【黄金 (Gold/XAU)】及相关市场的影响。

输入信息：
- 来源: {raw_data.get('source')}
- 作者: {raw_data.get('author')}
- 内容: {content}
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
    "sentiment_score": -1.0 to 1.0 (数值，-1为极度利空黄金，1为利好),
    "urgency_score": 1-10 (整数，10为极度重要),
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
            "name": "实体名称（如 Trump / Fed / EU Tariff）",
            "type": "person/organization/policy/country/commodity/other",
            "impact": "bullish/bearish/neutral"
        }}
    ],
    "relations": [
        {{
            "subject": "主体实体名",
            "predicate": "关系（如 raises_tariff / rate_hike / risk_off）",
            "object": "客体实体名",
            "direction": "forward/bidirectional",
            "strength": 0.0 to 1.0
        }}
    ]
}}
"""
