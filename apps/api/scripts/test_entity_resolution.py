import asyncio
import json
import os
import uuid

from dotenv import load_dotenv

# Load env before importing modules
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
ai_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env.ai")
load_dotenv(env_path)
load_dotenv(ai_env_path, override=True)

from src.lucidpanda.core.ontology import EntityResolver  # noqa: E402
from src.lucidpanda.providers.llm.gemini import GeminiLLM  # noqa: E402


async def test_entity_resolution_no_db():
    print("🚀 开始测试强化的实体识别与多维标签打标流水线 (无数据库依赖)...")

    # 1. 模拟一条复杂的突发新闻
    f"test_{uuid.uuid4().hex[:8]}"
    mock_content = "美联储主席鲍威尔今日在杰克逊霍尔年会上意外释放强烈的鸽派信号，暗示将在9月降息50个基点。同时，中东地区的紧张局势升级导致油价大涨。受此双重影响，国际金价短线飙升突破历史新高。"

    try:
        # 2. 初始化 GeminiLLM 和 EntityResolver
        print("🤖 初始化 Gemini LLM 分析器...")
        llm = GeminiLLM()
        resolver = EntityResolver()

        # 3. 模拟分析
        print("🤖 调用 AI 引擎开始分析并打标...")
        mock_news = {
            "content": mock_content,
            "url": "http://mock.url"
        }
        analysis_result = await llm.analyze_async(mock_news)

        # 4. 根据新流线，AI处理完后传入Resolver解析实体
        entities = analysis_result.get('entities', [])
        resolved_entities = resolver.process_ai_entities(entities)
        tags = analysis_result.get('tags', [])
        summary = analysis_result.get('summary', {})

        print("🔍 AI 提取与解析结果验证:")
        print(f"📝 AI 摘要: {summary.get('zh') if summary else 'N/A'}")

        print("\n📎 提取到的 tags:")
        print(json.dumps(tags, indent=2, ensure_ascii=False))

        print("\n🆔 提取并解析的 entities (检查 canonical_id):")
        print(json.dumps(resolved_entities, indent=2, ensure_ascii=False))

        # 简单验证逻辑
        has_powell_canonical = False
        has_middle_east_canonical = False

        if resolved_entities:
            for ent in resolved_entities:
                if ent.get('canonical_id') == 'ent_fed_powell':
                    has_powell_canonical = True
                if ent.get('canonical_id') == 'ent_geo_mideast':
                    has_middle_east_canonical = True

        print("\n✅ 测试验证结论:")
        if has_powell_canonical:
            print("✔️ 成功：'鲍威尔' 被正确规范化为 'ent_fed_powell'")
        else:
            print("❌ 失败：未识别到 '鲍威尔' 的标准ID聚合")

        if has_middle_east_canonical:
            print("✔️ 成功：'中东' 被正确规范化为 'ent_geo_mideast'")
        else:
            print("❌ 失败：未识别到 '中东' 的标准ID聚合")

        if tags and len(tags) > 0:
            print(f"✔️ 成功：多维标签被成功附加，共 {len(tags)} 个")
        else:
            print("❌ 失败：无可用 tags")

    except Exception as e:
        print(f"❌ 测试执行异常: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_entity_resolution_no_db())
