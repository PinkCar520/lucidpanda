import asyncio
from datetime import UTC, datetime

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.lucidpanda.config import settings
from src.lucidpanda.core.logger import logger


class FredDataSource:
    """
    美联储经济数据 (FRED) 官方结构化接口
    完全免费、无反爬、毫秒级响应。专门获取宏观经济核心指标的数值。
    """
    BASE_URL = "https://api.stlouisfed.org/fred/series/observations"

    MACRO_INDICATORS = {
        "FEDFUNDS": "联邦基金实际利率 (Federal Funds Effective Rate)",
        "CPIAUCSL": "美国消费者物价指数序列 (CPI - All Urban Consumers)",
        "UNRATE": "美国官方失业率 (Unemployment Rate)",
        "PAYEMS": "美国非农就业总人数 (Total Nonfarm Payrolls)",
        "T10Y2Y": "10年期减2年期美债收益率利差 (收益率倒挂指标)",
        "DEXUSEU": "美元兑欧元汇率快照",
    }

    def __init__(self, api_key: str = None):
        self.api_key = api_key or getattr(settings, "FRED_API_KEY", None)
        if not self.api_key:
            logger.warning("⚠️ 缺失 FRED_API_KEY，美联储结构化大盘数据服务将无法使用！")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((httpx.ConnectError, httpx.ReadTimeout, httpx.ConnectTimeout)),
        reraise=True
    )
    async def fetch_series(self, client: httpx.AsyncClient, series_id: str, limit: int = 1) -> list[dict] | None:
        if not self.api_key:
            return None

        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit
        }

        response = await client.get(self.BASE_URL, params=params, timeout=10.0)
        
        if response.status_code != 200:
            logger.error(f"❌ FRED抓取失败 [{series_id}]: HTTP {response.status_code} - {response.text}")
            return None

        data = response.json()
        observations = data.get("observations", [])
        
        results = []
        for obs in observations:
            results.append({
                "series_id": series_id,
                "name": self.MACRO_INDICATORS.get(series_id, "Unknown"),
                "date": obs.get("date"),
                "value": obs.get("value"),
                "ingested_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            })
            
        return results

    async def fetch_macro_dashboard(self) -> dict:
        """
        并发抓取，瞬间拉齐当前所有的宏观底座核心数据！
        """
        if not self.api_key:
            return {}
            
        logger.info("🇺🇸 开始调用美联储 FRED 官方接口拉取大盘快照...")
        
        async with httpx.AsyncClient(verify=True) as client:
            tasks = [self.fetch_series(client, series_id) for series_id in self.MACRO_INDICATORS.keys()]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
        dashboard = {}
        for series_id, res in zip(self.MACRO_INDICATORS.keys(), results, strict=False):
            if isinstance(res, Exception):
                logger.error(f"⚠️ 获取宏观指标 {series_id} 出现异常：{res}")
                dashboard[series_id] = None
            elif res and len(res) > 0:
                dashboard[series_id] = res[0]
                
        logger.info(f"✅ 美联储宏观快照获取完毕，成功获取 {len([k for k,v in dashboard.items() if v])} 项指标。")
        return dashboard
