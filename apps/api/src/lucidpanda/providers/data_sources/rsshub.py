"""
LucidPanda RSS Intelligence Source
=====================================
分类情报引擎：支持黄金宏观、A股政策、美股权益信源的分离采集与精准过滤。
"""

import asyncio
import os
import feedparser
import httpx
from src.lucidpanda.core.logger import logger
from src.lucidpanda.providers.data_sources.base import BaseDataSource


# ──────────────────────────────────────────────────────────────────────
# 1. 黄金宏观信源 (Category: macro_gold)
# ──────────────────────────────────────────────────────────────────────
MACRO_GOLD_FEEDS = [
    ("Trump Truth Social",     "https://www.trumpstruth.org/feed"),
    ("WhiteHouse Exec Orders", "https://www.whitehouse.gov/presidential-actions/feed/"),
    ("Politico Politics",      "https://rss.politico.com/politics-news.xml"),
    ("Bloomberg Economics",    "https://feeds.bloomberg.com/economics/news.rss"),
    ("Fed Speeches",           "https://www.federalreserve.gov/feeds/speeches.xml"),
    ("Fed Press Releases",     "https://www.federalreserve.gov/feeds/press_all.xml"),
    ("WSJ Economy",            "https://feeds.content.dowjones.io/public/rss/socialeconomyfeed"),
    ("CFTC Press Releases",    "http://rsshub:1200/cftc/pressreleases"),
]

# ──────────────────────────────────────────────────────────────────────
# 2. A股政策与快讯 (Category: equity_cn)
# ──────────────────────────────────────────────────────────────────────
EQUITY_CN_FEEDS = [
    ("财联社-深度",           "http://rsshub:1200/cls/telegraph/depth"),
    ("财联社-电报",           "http://rsshub:1200/cls/telegraph"),
    ("证券时报-网快讯",          "http://rsshub:1200/stcn/article/list/kx"),
    ("华尔街见闻-A股",         "http://rsshub:1200/wallstreetcn/news/a-stock"),
    ("上交所-信息披露",        "http://rsshub:1200/sse/disclosure"),
    ("深交所-上市公告",        "http://rsshub:1200/szse/disclosure/listed/notice"),
]

# ──────────────────────────────────────────────────────────────────────
# 3. 美股权益与行业 (Category: equity_us)
# ──────────────────────────────────────────────────────────────────────
EQUITY_US_FEEDS = [
    ("CNBC Technology",        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"),
    ("Bloomberg Markets",      "https://feeds.bloomberg.com/markets/news.rss"),
    ("WSJ Markets",            "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"),
    ("MarketWatch-Top",        "https://feeds.content.dowjones.io/public/rss/mw_topstories"),
    ("Yahoo Finance-News",      "https://finance.yahoo.com/news/rssindex"),
    ("Reuters-Business",       "http://rsshub:1200/reuters/business"),
]

# 汇总所有信源并标记分类
TIER1_FEEDS_CONFIG = []
for name, url in MACRO_GOLD_FEEDS:
    TIER1_FEEDS_CONFIG.append({"name": name, "url": url, "category": "macro_gold"})
for name, url in EQUITY_CN_FEEDS:
    TIER1_FEEDS_CONFIG.append({"name": name, "url": url, "category": "equity_cn"})
for name, url in EQUITY_US_FEEDS:
    TIER1_FEEDS_CONFIG.append({"name": name, "url": url, "category": "equity_us"})


# ──────────────────────────────────────────────
# 内容过滤关键词桶
# ──────────────────────────────────────────────

# 噪音黑名单
_NOISE_KEYWORDS = frozenset([
    "nfl", "nba", "soccer", "olympic", "grammy", "oscar",
    "celebrity", "recipe", "fashion", "lifestyle", "dating",
])

# 黄金宏观桶
_GOLD_MACRO_KEYWORDS = frozenset([
    "gold", "xau", "silver", "precious metal", "bullion", "fed ", "fomc", 
    "interest rate", "inflation", "cpi", "pce", "dxy", "treasury", "yield",
    "geopolit", "war", "sanction", "trump", "tariff",
])

# A股政策桶
_CN_POLICY_KEYWORDS = frozenset([
    "指导意见", "扶持", "降准", "降息", "准备金", "房地产", "化债", "财政",
    "高质量发展", "新质生产力", "监管", "证监会", "深交所", "上交所", "IPO", "再融资",
    "半导体", "集成电路", "人工智能", "生物医药", "低空经济", "新能源", "以旧换新",
])

# 美股权益桶
_US_EQUITY_KEYWORDS = frozenset([
    "earnings", "revenue", "guidance", "buyback", "dividend", "acquisition", "merger",
    "tech", "ai", "semiconductor", "chip", "nvidia", "apple", "microsoft", "tesla", 
    "google", "amazon", "meta", "fed ", "rate", "unemployment", "gdp",
])

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class RSSHubSource(BaseDataSource):
    def __init__(self, db=None):
        super().__init__(db)
        self.feed_configs = TIER1_FEEDS_CONFIG
        self._semaphore: asyncio.Semaphore | None = None
        # 开启后打印每个信源的抓取结果，便于灰度排查失效信源
        self.log_each_source = os.getenv("LUCIDPANDA_LOG_EACH_SOURCE", "1").lower() not in {
            "0", "false", "off"
        }

    def _is_noise(self, text: str) -> bool:
        return any(kw in text for kw in _NOISE_KEYWORDS)

    def _passes_category_filter(self, category: str, text: str) -> bool:
        """根据情报分类应用不同的过滤策略。"""
        if category == "macro_gold":
            return any(kw in text for kw in _GOLD_MACRO_KEYWORDS)
        if category == "equity_cn":
            # A股政策类信源放行门槛稍低，优先捕获政策动向
            return any(kw in text for kw in _CN_POLICY_KEYWORDS) or len(text) > 100
        if category == "equity_us":
            return any(kw in text for kw in _US_EQUITY_KEYWORDS)
        return False

    async def _fetch_feed_async(
        self,
        client: httpx.AsyncClient,
        ssl_client: httpx.AsyncClient,
        config: dict,
    ) -> tuple[list[dict], dict]:
        name = config["name"]
        url = config["url"]
        category = config["category"]
        status = {
            "name": name,
            "url": url,
            "category": category,
            "status": "unknown",
            "new_items": 0,
            "total_entries": 0,
            "dedup_skipped": 0,
            "filter_skipped": 0,
            "reason": "",
        }
        
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        active_client = ssl_client if "reuters" in host else client

        async with self._semaphore:
            try:
                resp = await active_client.get(url, timeout=15.0)
                if resp.status_code != 200:
                    status["status"] = "failed"
                    status["reason"] = f"HTTP {resp.status_code}"
                    return [], status
                
                feed = feedparser.parse(resp.content)
                if not feed.entries:
                    status["status"] = "ok_empty"
                    status["reason"] = "feed 无条目"
                    return [], status
                status["total_entries"] = len(feed.entries)

                # DB 批量去重
                all_ids = [getattr(e, "id", None) or getattr(e, "link", None) for e in feed.entries]
                all_ids = [i for i in all_ids if i]
                existing_ids = await asyncio.to_thread(self.db.source_ids_batch_exists, all_ids) if self.db else set()

                items = []
                for entry in feed.entries:
                    item_id = getattr(entry, "id", None) or getattr(entry, "link", None)
                    if not item_id or item_id in existing_ids:
                        status["dedup_skipped"] += 1
                        continue

                    title = getattr(entry, "title", "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    full_text = f"{title} {summary}".lower()

                    if self._is_noise(full_text):
                        status["filter_skipped"] += 1
                        continue
                    if not self._passes_category_filter(category, full_text):
                        status["filter_skipped"] += 1
                        continue

                    items.append({
                        "source": name,
                        "author": name,
                        "category": category,
                        "timestamp": getattr(entry, "published", ""),
                        "content": f"{title}. {summary}",
                        "url": getattr(entry, "link", url),
                        "id": item_id,
                    })
                status["new_items"] = len(items)
                status["status"] = "ok_new" if items else "ok_empty"
                if not items:
                    status["reason"] = "过滤/去重后无新增"
                return items, status
            except Exception as e:
                status["status"] = "failed"
                status["reason"] = str(e)
                logger.warning(f"⚠️ [{name}] 抓取失败: {e}")
                return [], status

    async def fetch_async(self) -> list | None:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(8)

        async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=True) as client, \
                   httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=False) as ssl_client:
            tasks = [self._fetch_feed_async(client, ssl_client, cfg) for cfg in self.feed_configs]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        new_items = []
        source_statuses = []
        for res in results:
            if isinstance(res, Exception):
                source_statuses.append({
                    "name": "unknown",
                    "url": "",
                    "category": "",
                    "status": "failed",
                    "new_items": 0,
                    "total_entries": 0,
                    "dedup_skipped": 0,
                    "filter_skipped": 0,
                    "reason": str(res),
                })
                continue

            items, status = res
            new_items.extend(items)
            source_statuses.append(status)

        if self.log_each_source:
            for s in source_statuses:
                if s["status"] == "failed":
                    logger.warning(
                        f"❌ [RSS:{s['category']}] {s['name']} | 失败 | {s['reason']} | {s['url']}"
                    )
                else:
                    logger.info(
                        f"🧪 [RSS:{s['category']}] {s['name']} | {s['status']} | "
                        f"entries={s['total_entries']} | new={s['new_items']} | "
                        f"dedup={s['dedup_skipped']} | filtered={s['filter_skipped']}"
                    )

        failed = sum(1 for s in source_statuses if s["status"] == "failed")
        ok_new = sum(1 for s in source_statuses if s["status"] == "ok_new")
        ok_empty = sum(1 for s in source_statuses if s["status"] == "ok_empty")
        logger.info(
            f"📈 RSS信源汇总: total={len(source_statuses)} | ok_new={ok_new} | "
            f"ok_empty={ok_empty} | failed={failed}"
        )
        
        if new_items:
            logger.info(f"✅ 分类采集完毕: 总计 {len(new_items)} 条新情报")
        return new_items if new_items else None

    def fetch(self) -> list | None:
        return asyncio.run(self.fetch_async())
