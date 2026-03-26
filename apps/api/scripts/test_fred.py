import asyncio
import os
import sys

# 确保项目路径可用
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
# 还需要添加 apps/api/src 到路径
api_src = os.path.join(root_dir, "apps/api")
if api_src not in sys.path:
    sys.path.insert(0, api_src)

from src.lucidpanda.config import settings
from src.lucidpanda.providers.data_sources.fred import FredDataSource


async def main():
    print(f"🔍 Testing FRED API with Key: {settings.FRED_API_KEY[:4]}...")
    fred = FredDataSource()

    try:
        dashboard = await fred.fetch_macro_dashboard()
        if not dashboard:
            print("❌ Failed to fetch dashboard (is API key set?)")
            return

        print("\n✅ Macro Dashboard Fetched:")
        for k, v in dashboard.items():
            if v:
                print(f"  - {v['name']} ({k}): {v['value']} (Date: {v['date']})")
            else:
                print(f"  - {k}: Failed")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())
