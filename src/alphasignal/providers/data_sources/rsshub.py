"""
AlphaSignal RSS Intelligence Source
=====================================
第一梯队极速宏观情报引擎，直接对接各大权威媒体的官方 RSS Feed。

架构设计原则：
1. 零中间层：绕过 rsshub.app 公共节点，直连媒体官方 Feed（更稳定、更低延迟）
2. 精准聚焦：所有信源均围绕黄金价格的宏观驱动因子选取
3. DB 级去重：通过 IntelligenceDB.source_ids_batch_exists() 做批量去重，
   彻底替代原来的文件状态方案，支持多进程/多容器场景
4. 三级内容过滤：噪音黑名单 → 信源专属策略 → 黄金宏观关键词
5. 所有 Feed URL 均经过实际 HTTP 200 + RSS 格式验证（2026-02-28）
"""

import requests
import feedparser
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.data_sources.base import BaseDataSource


# ──────────────────────────────────────────────
# RSS 信源配置（经过实测验证，HTTP 200）
# 格式：(显示名称, RSS URL)
# ──────────────────────────────────────────────
TIER1_FEEDS = [
    # ── 政治风险层（黄金最直接的驱动力）────────────────────────────────
    ("Trump Truth Social",     "https://www.trumpstruth.org/feed"),
    ("WhiteHouse Exec Orders", "https://www.whitehouse.gov/presidential-actions/feed/"),

    # ── 彭博社 Bloomberg ─────────────────────────────────────────────
    ("Bloomberg Markets",      "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Economics",    "https://feeds.bloomberg.com/economics/news.rss"),
    ("Bloomberg Top News",     "https://feeds.bloomberg.com/bview/news.rss"),

    # ── 华尔街日报 WSJ ───────────────────────────────────────────────
    ("WSJ Markets",            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("WSJ Economy",            "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"),
    ("WSJ Full (feedx)",       "https://feedx.net/rss/wsj.xml"),

    # ── 纽约时报 NYT ─────────────────────────────────────────────────
    ("NYT Top News",           "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),

    # ── CNBC ────────────────────────────────────────────────────────
    ("CNBC Top News",          "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC Finance",           "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC Economy",           "https://www.cnbc.com/id/20910258/device/rss/rss.html"),

    # ── 金融时报 FT ──────────────────────────────────────────────────
    ("Financial Times",        "https://www.ft.com/?format=rss"),

    # ── 路透社 Reuters（本地 SSL 问题，腾讯云服务器上正常）────────────────
    ("Reuters Top News",       "https://feeds.reuters.com/reuters/topNews"),
    ("Reuters Business",       "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Commodities",    "https://feeds.reuters.com/reuters/commoditiesNews"),
]


# ──────────────────────────────────────────────
# 内容过滤关键词
# ──────────────────────────────────────────────

# 噪音黑名单：命中任意一词 → 直接拦截（所有信源通用）
_NOISE_KEYWORDS = frozenset([
    "nfl", "nba", "soccer", "olympic", "grammy", "oscar",
    "celebrity", "recipe", "fashion", "lifestyle", "dating",
    "relationship", "epstein", "clinton scandal", "reality tv",
])

# 黄金宏观驱动关键词：命中任意一词 → 放行（彭博/CNBC/WSJ 等通用信源使用）
_GOLD_RELEVANCE_KEYWORDS = frozenset([
    "gold", "xau", "silver", "precious metal", "bullion", "spot price", "comex", "lbma",
    "trump", "white house", "executive order", "mar-a-lago", "administration", "tariff",
    "federal reserve", "fed ", "fomc", "interest rate", "rate cut", "rate hike",
    "powell", "monetary policy", "quantitative", "balance sheet",
    "inflation", "cpi", "pce", "deflation", "stagflation",
    "gdp", "recession", "jobs report", "nonfarm", "unemployment",
    "dollar", "dxy", "treasury", "yield", "bond", "10-year", "debt",
    "currency", "forex", "fx ",
    "geopolit", "war", "conflict", "sanction", "iran", "russia", "ukraine",
    "middle east", "oil", "opec", "energy crisis",
    "safe haven", "crisis", "crash", "collapse", "bank run",
    "systemic", "contagion", "liquidity", "credit risk",
    "trade war", "trade deal", "import tax",
])

# Trump Truth Social 二次严格过滤：必须含有宏观/地缘/市场关键词才放行
# 目的：排除选举背书帖、体育评论帖、娱乐八卦帖
_TRUMP_MACRO_KEYWORDS = frozenset([
    "tariff", "trade", "sanction", "tax", "economy", "economic",
    "inflation", "dollar", "debt", "deficit", "budget",
    "treasury", "reserve", "rate", "fed", "interest",
    "iran", "russia", "ukraine", "china", "war", "military",
    "nato", "middle east", "oil", "energy",
    "gold", "silver", "market", "stock", "crypto", "bitcoin",
])

_REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class RSSHubSource(BaseDataSource):
    """
    第一梯队黄金宏观情报 RSS 引擎。
    使用 DB 级批量去重，彻底替代原有的文件状态方案。
    """

    def __init__(self, db=None):
        super().__init__(db)
        self.feeds = TIER1_FEEDS

    # ──────────────────────────────────────────────
    # 内容过滤器
    # ──────────────────────────────────────────────

    def _is_noise(self, text: str) -> bool:
        return any(kw in text for kw in _NOISE_KEYWORDS)

    def _is_gold_relevant(self, text: str) -> bool:
        return any(kw in text for kw in _GOLD_RELEVANCE_KEYWORDS)

    def _is_trump_macro(self, text: str) -> bool:
        return any(kw in text for kw in _TRUMP_MACRO_KEYWORDS)

    def _passes_filter(self, source_name: str, title: str, summary: str) -> bool:
        """统一过滤调度入口，按信源类型选择对应策略。"""
        text = f"{title} {summary}".lower()
        if self._is_noise(text):
            return False
        if source_name == "Trump Truth Social":
            return self._is_trump_macro(text)
        return self._is_gold_relevant(text)

    # ──────────────────────────────────────────────
    # 主抓取逻辑
    # ──────────────────────────────────────────────

    def fetch(self) -> list | None:
        """
        遍历所有 Tier-1 RSS 信源，经 DB 去重 + 三级内容过滤后，
        返回本轮新发现的黄金情报列表。
        """
        new_items = []
        total_fetched = 0
        total_filtered = 0
        total_db_skipped = 0

        for name, url in self.feeds:
            logger.info(f"正在扫描: {name}")
            try:
                resp = requests.get(url, headers=_REQUEST_HEADERS, timeout=12)
                if resp.status_code != 200:
                    logger.warning(f"❌ [{name}] HTTP {resp.status_code}")
                    continue

                feed = feedparser.parse(resp.content)
                if not feed.entries:
                    continue

                # ── DB 批量去重：一次查询过滤整个 Feed ──────────────────
                all_ids = [
                    getattr(e, "id", None) or getattr(e, "link", None)
                    for e in feed.entries
                ]
                all_ids = [i for i in all_ids if i]

                existing_ids = (
                    self.db.source_ids_batch_exists(all_ids)
                    if self.db else set()
                )
                total_db_skipped += len(existing_ids)

                # ── 内容过滤 ─────────────────────────────────────────
                for entry in feed.entries:
                    item_id = getattr(entry, "id", None) or getattr(entry, "link", None)
                    if not item_id or item_id in existing_ids:
                        continue

                    title   = getattr(entry, "title",   "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    total_fetched += 1

                    if not self._passes_filter(name, title, summary):
                        total_filtered += 1
                        continue

                    logger.info(f"🔥 [{name}] {title[:70]}...")
                    new_items.append({
                        "source":    name,
                        "author":    name,
                        "timestamp": getattr(entry, "published", ""),
                        "content":   f"{title}. {summary}",
                        "url":       getattr(entry, "link", url),
                        "id":        item_id,
                    })

            except requests.exceptions.Timeout:
                logger.warning(f"⏱ [{name}] 超时，跳过")
            except Exception as e:
                logger.error(f"❌ [{name}] 抓取异常: {e}")

        logger.info(
            f"✅ RSS 本轮完毕 | DB跳过 {total_db_skipped} | "
            f"新读取 {total_fetched} | 过滤噪音 {total_filtered} | "
            f"黄金信号 {len(new_items)} 条 → AI 分析"
        )
        return new_items if new_items else None
