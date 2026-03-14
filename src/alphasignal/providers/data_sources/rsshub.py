"""
AlphaSignal RSS Intelligence Source
=====================================
分类情报引擎：支持黄金宏观、A股政策、美股权益信源的分离采集与精准过滤。
"""

import asyncio
import feedparser
import httpx
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.data_sources.base import BaseDataSource


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
    ("国务院政策公告",         "http://rsshub:1200/gov/zhengce/zuixin"),
    ("证监会发布",             "http://rsshub:1200/csrc/news"),
    ("央行公告",               "http://rsshub:1200/pbc/gonggao"),
    ("财联社政策快讯",         "http://rsshub:1200/cls/telegraph/depth"),
    ("华尔街见闻-A股",         "http://rsshub:1200/wallstreetcn/news/a-stock"),
    ("证券时报-发行监管",       "http://rsshub:1200/stcn/news/fxjg"),
]

# ──────────────────────────────────────────────────────────────────────
# 3. 美股权益与行业 (Category: equity_us)
# ──────────────────────────────────────────────────────────────────────
EQUITY_US_FEEDS = [
    ("CNBC Technology",        "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19854910"),
    ("Bloomberg Markets",      "https://feeds.bloomberg.com/markets/news.rss"),
    ("WSJ Markets",            "https://feeds.content.dowjones.io/public/rss/RSSMarketsMain"),
    ("Reuters Business",       "http://rsshub:1200/reuters/category/businessNews"),
    ("Reuters Tech",           "http://rsshub:1200/reuters/category/technologyNews"),
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
    ) -> list[dict]:
        name = config["name"]
        url = config["url"]
        category = config["category"]
        
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        active_client = ssl_client if "reuters" in host else client

        async with self._semaphore:
            try:
                resp = await active_client.get(url, timeout=15.0)
                if resp.status_code != 200:
                    logger.warning(f"⚠️ [{name}] 抓取失败: HTTP {resp.status_code}")
                    return []
                
                feed = feedparser.parse(resp.content)
                if not feed.entries:
                    logger.info(f"🧪 [{name}] ok_empty | entries=0 | new=0 | dedup=0 | filtered=0")
                    return []

                # DB 批量去重
                all_ids = [getattr(e, "id", None) or getattr(e, "link", None) for e in feed.entries]
                all_ids = [i for i in all_ids if i]
                existing_ids = await asyncio.to_thread(self.db.source_ids_batch_exists, all_ids) if self.db else set()

                items = []
                dedup_skipped = 0
                filter_skipped = 0
                for entry in feed.entries:
                    item_id = getattr(entry, "id", None) or getattr(entry, "link", None)
                    if not item_id or item_id in existing_ids:
                        dedup_skipped += 1
                        continue

                    title = getattr(entry, "title", "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    full_text = f"{title} {summary}".lower()

                    if self._is_noise(full_text):
                        filter_skipped += 1
                        continue
                    if not self._passes_category_filter(category, full_text):
                        filter_skipped += 1
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

                status = "ok_new" if items else "ok_empty"
                logger.info(
                    f"🧪 [{name}] {status} | entries={len(feed.entries)} | new={len(items)} | "
                    f"dedup={dedup_skipped} | filtered={filter_skipped}"
                )
                return items
            except Exception as e:
                logger.warning(f"⚠️ [{name}] 抓取失败: {e}")
                return []

    async def fetch_async(self) -> list | None:
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(8)

        async with httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=True) as client, \
                   httpx.AsyncClient(headers=_DEFAULT_HEADERS, verify=False) as ssl_client:
            tasks = [self._fetch_feed_async(client, ssl_client, cfg) for cfg in self.feed_configs]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        new_items = []
        for res in results:
            if isinstance(res, list): new_items.extend(res)
        
        if new_items:
            logger.info(f"✅ 分类采集完毕: 总计 {len(new_items)} 条新情报")
        return new_items if new_items else None

    def fetch(self) -> list | None:
        return asyncio.run(self.fetch_async())
