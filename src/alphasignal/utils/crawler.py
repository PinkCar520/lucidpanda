import httpx
import asyncio
import re
from src.alphasignal.core.logger import logger

class AsyncRichCrawler:
    """
    工业级异步全文提取器
    支持 Jina Reader 穿透、Markdown 格式化、超时熔断与自动重试。
    """
    JINA_BASE_URL = "https://r.jina.ai/"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def __init__(self, max_concurrent=10, timeout=12):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.timeout = timeout
        self.client_limits = httpx.Limits(max_keepalive_connections=5, max_connections=max_concurrent)

    async def _fetch_single(self, client: httpx.AsyncClient, url: str, item_id: str):
        """抓取单条链接的全文，带重试逻辑"""
        jina_url = f"{self.JINA_BASE_URL}{url}"
        headers = {
            "User-Agent": self.USER_AGENT,
            "X-Return-Format": "markdown",
            "X-With-Generated-Alt": "true"
        }

        async with self.semaphore:
            for attempt in range(2): # 最多尝试 2 次
                try:
                    response = await client.get(jina_url, headers=headers, timeout=self.timeout)
                    if response.status_code == 200:
                        content = response.text
                        # 简单的清洗：去除 Jina Reader 的页眉页脚（如有）
                        content = re.sub(r'URL Source:.*\n', '', content)
                        content = re.sub(r'Published Time:.*\n', '', content)
                        if len(content.strip()) > 200: # 长度校验，确保不是空页面
                            return content.strip()
                    elif response.status_code == 429:
                        logger.warning(f"Jina Reader Rate Limited (429) for {url}, retrying...")
                        await asyncio.sleep(2)
                    else:
                        logger.warning(f"Jina Reader error {response.status_code} for {url}")
                except Exception as e:
                    if attempt == 1:
                        logger.warning(f"Failed to fetch full text after retries {url}: {e}")
            return None

    async def batch_crawl(self, items: list):
        """并行抓取一批情报的全文"""
        if not items:
            return items

        async with httpx.AsyncClient(limits=self.client_limits, follow_redirects=True) as client:
            tasks = []
            for item in items:
                tasks.append(self._fetch_single(client, item['url'], item.get('id')))
            
            results = await asyncio.gather(*tasks)

            processed_count = 0
            for i, full_text in enumerate(results):
                if full_text:
                    items[i]['content'] = full_text
                    items[i]['extraction_method'] = "JINA_READER"
                    processed_count += 1
                else:
                    items[i]['extraction_method'] = "RSS_SUMMARY"
            
            logger.info(f"✅ 全文提取任务完成: {processed_count}/{len(items)} 成功获取全文。")
        return items
