import asyncio
import os
import sys

# 确保项目路径可用
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)
api_src = os.path.join(root_dir, "apps/api")
if api_src not in sys.path:
    sys.path.insert(0, api_src)

from src.lucidpanda.config import settings
from src.lucidpanda.providers.data_sources.email_source import EmailDataSource


async def main():
    print("📧 Testing Email/IMAP Ingestion...")
    print(f"Server: {settings.IMAP_SERVER}")
    print(f"User: {settings.IMAP_USER}")

    source = EmailDataSource()

    # 模拟抓取
    try:
        items = await source.fetch_async()
        if items is None:
            print("ℹ️ No new official emails found (or config missing).")
        else:
            print(f"✅ Found {len(items)} official emails.")
            for item in items:
                print(f"  - [{item['source']}] {item['content'][:100]}...")
    except Exception as e:
        print(f"❌ Error during email fetch: {e}")

if __name__ == "__main__":
    asyncio.run(main())
