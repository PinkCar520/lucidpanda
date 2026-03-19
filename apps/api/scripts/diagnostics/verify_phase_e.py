
import asyncio
import sys
import os
from datetime import datetime

# Ensure project root is in path
root_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.services.embedding_service import embedding_service
from src.lucidpanda.services.agent_tools import call_tool, list_tool_summaries
from src.lucidpanda.core.logger import logger

async def verify_embedding():
    print("\n--- 1. 验证 Embedding 稳定性与降级 ---")
    text = "测试黄金市场情绪分析"
    try:
        # This will trigger either Gemini or Local fallback
        vector = embedding_service.encode(text)
        print(f"✅ Embedding 成功生成! 维度: {len(vector)}")
    except Exception as e:
        print(f"❌ Embedding 失败: {e}")

async def verify_tools():
    print("\n--- 2. 验证新工具补全 ---")
    tools = list_tool_summaries()
    tool_names = [t['name'] for t in tools]
    required_tools = ['get_historical_perf', 'get_market_positioning', 'get_entity_influence']
    
    for rt in required_tools:
        if rt in tool_names:
            print(f"✅ 工具 '{rt}' 已注册。")
        else:
            print(f"❌ 工具 '{rt}' 缺失!")

    # Test get_historical_perf
    print("\n测试 get_historical_perf ('黄金')...")
    res = call_tool("get_historical_perf", {"keywords": "黄金"})
    print(f"结果: {res}")

    # Test get_market_positioning
    print("\n测试 get_market_positioning...")
    res = call_tool("get_market_positioning", {})
    print(f"结果: {res}")

    # Test get_entity_influence (Assuming 'Gold' exists in graph)
    print("\n测试 get_entity_influence ('Gold')...")
    res = call_tool("get_entity_influence", {"entity_name": "Gold"})
    print(f"结果: {res}")

async def main():
    await verify_embedding()
    await verify_tools()
    print("\n--- 验证结束 ---")

if __name__ == "__main__":
    asyncio.run(main())
