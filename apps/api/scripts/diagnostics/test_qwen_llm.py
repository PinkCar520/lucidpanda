#!/usr/bin/env python
"""
测试 QwenLLM (阿里云百炼) 是否正常工作
使用方法：
    cd apps/api
    python scripts/diagnostics/test_qwen_llm.py
"""
import os
import sys

# Ensure project root is in path (与其他诊断脚本保持一致)
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.config import settings
from src.lucidpanda.providers.llm.qwen_llm import QwenLLM


def test_qwen_llm():
    print("=" * 60)
    print("🧪 QwenLLM (阿里云百炼) 测试")
    print("=" * 60)
    print()

    # 检查配置
    print("1. 检查配置...")
    print(f"   AI_PROVIDER: {settings.AI_PROVIDER}")
    print(f"   QWEN_MODEL: {settings.QWEN_MODEL}")
    print(f"   QWEN_BASE_URL: {settings.QWEN_BASE_URL}")
    print(f"   QWEN_API_KEY: {'✅ 已配置' if settings.QWEN_API_KEY else '❌ 未配置'}")
    print()

    if not settings.QWEN_API_KEY or settings.QWEN_API_KEY == "your_qwen_api_key_here":
        print("❌ 请先在 .env.ai 中配置 QWEN_API_KEY")
        print("   获取地址：https://bailian.console.aliyun.com/")
        return False

    # 创建 LLM 实例
    print("2. 创建 QwenLLM 实例...")
    llm = QwenLLM()
    print("   ✅ 实例创建成功")
    print()

    # 测试单条分析
    print("3. 测试单条新闻分析...")
    test_news = {
        "source": "新华社",
        "author": "记者",
        "content": "美联储主席鲍威尔表示，鉴于当前通胀压力持续存在，美联储可能会在下次会议上再次加息 25 个基点。他指出，劳动力市场依然紧张，消费支出保持强劲，但地缘政治风险可能对经济前景构成威胁。",
        "context": "当前黄金价格：$2050/盎司，美元指数：103.5"
    }

    try:
        result = llm.analyze(test_news)
        print("   ✅ 分析成功！")
        print()
        print("   结果预览:")
        print(f"   - summary.zh: {result.get('summary', {}).get('zh', 'N/A')[:50]}...")
        print(f"   - sentiment_score: {result.get('sentiment_score', 'N/A')}")
        print(f"   - urgency_score: {result.get('urgency_score', 'N/A')}")
        print(f"   - entities: {len(result.get('entities', []))} 个")
        print(f"   - relations: {len(result.get('relations', []))} 个")
        print()

        # 验证输出格式
        print("4. 验证输出格式...")
        required_fields = ['summary', 'sentiment', 'sentiment_score', 'urgency_score',
                          'market_implication', 'actionable_advice', 'entities', 'relations']
        missing = [f for f in required_fields if f not in result]
        if missing:
            print(f"   ⚠️  缺少字段：{missing}")
        else:
            print("   ✅ 所有必需字段都存在")

        print()
        print("=" * 60)
        print("✅ QwenLLM 测试通过！可以投入使用")
        print("=" * 60)
        return True

    except Exception as e:
        print(f"   ❌ 分析失败：{e}")
        print()
        print("   可能原因:")
        print("   1. API Key 无效")
        print("   2. 网络连接问题")
        print("   3. 配额已用完")
        print()
        print("   请检查:")
        print("   - .env.qwen 中的 QWEN_API_KEY 是否正确")
        print("   - 访问 https://bailian.console.aliyun.com/ 查看配额")
        return False

if __name__ == '__main__':
    success = test_qwen_llm()
    sys.exit(0 if success else 1)
