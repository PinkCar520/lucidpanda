import asyncio
import os

import httpx

# 模拟环境变量
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8001/api/v1")

async def test_pulse_api():
    print(f"🔍 Testing Analytics API at {API_BASE_URL}...")

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. 测试热点接口
        print("\n--- Testing Hotspots ---")
        try:
            resp = await client.get(f"{API_BASE_URL}/analytics/pulse/hotspots?days=7&limit=5")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Hotspots Success! Found {data.get('count')} items.")
                for item in data.get("hotspots", []):
                    print(f"  - {item.get('display_name')} ({item.get('canonical_id')}): {item.get('total_mentions')} mentions")
            else:
                print(f"❌ Hotspots Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Hotspots Request Error: {e}")

        # 2. 测试趋势接口 (使用鲍威尔 ID)
        print("\n--- Testing Entity Trend (Powell) ---")
        cid = "ent_fed_powell"
        try:
            resp = await client.get(f"{API_BASE_URL}/analytics/pulse/trend/{cid}?days=7")
            if resp.status_code == 200:
                data = resp.json()
                print(f"✅ Trend Success for {data.get('display_name')}!")
                for point in data.get("trend", []):
                    print(f"  - {point.get('metric_date')}: Sentiment={point.get('avg_sentiment'):.2f}, Mentions={point.get('mention_count')}")
            else:
                print(f"❌ Trend Failed: {resp.status_code} - {resp.text}")
        except Exception as e:
            print(f"❌ Trend Request Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_pulse_api())
