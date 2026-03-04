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
5. 并发采集：asyncio.gather() + httpx.AsyncClient，14 个信源同时拉取
   最坏耗时从原来的 ~210s 降低到单个最慢 Feed 的耗时（约 15s）
"""

import asyncio
import feedparser
import httpx
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.data_sources.base import BaseDataSource


# ──────────────────────────────────────────────
# RSS 信源配置（经过实测验证，HTTP 200）
# 格式：(显示名称, RSS URL)
# ──────────────────────────────────────────────
TIER1_FEEDS = [
    # ── 政治风险层（黄金最直接的驱动力）────────────────────────────────
    # 通过自建 RSSHub 容器代理境外信源，无需 Clash
    ("Trump Truth Social",     "http://rsshub:1200/twitter/user/realDonaldTrump"),
    ("WhiteHouse Exec Orders", "http://rsshub:1200/whitehouse/presidential-actions"),

    # ── 彭博社 Bloomberg ─────────────────────────────────────────────
    ("Bloomberg Markets",      "http://rsshub:1200/bloomberg/markets"),
    ("Bloomberg Economics",    "http://rsshub:1200/bloomberg/economics"),
    ("Bloomberg Top News",     "http://rsshub:1200/bloomberg/technology"),  # top news

    # ── 华尔街日报 WSJ ───────────────────────────────────────────────
    ("WSJ Markets",            "http://rsshub:1200/wsj/market"),
    ("WSJ Economy",            "http://rsshub:1200/wsj/economy"),

    # ── 纽约时报 NYT ─────────────────────────────────────────────────
    ("NYT Top News",           "http://rsshub:1200/nytimes/homepage"),

    # ── CNBC ────────────────────────────────────────────────────────
    ("CNBC Top News",          "http://rsshub:1200/cnbc/news/100003114"),
    ("CNBC Finance",           "http://rsshub:1200/cnbc/news/10000664"),
    ("CNBC Economy",           "http://rsshub:1200/cnbc/news/20910258"),

    # ── 金融时报 FT ──────────────────────────────────────────────────
    ("Financial Times",        "http://rsshub:1200/ft/myft/personal-finance"),

    # ── 路透社 Reuters ────────────────────────────────────────────────
    ("Reuters Top News",       "http://rsshub:1200/reuters/category/topnews"),
    ("Reuters Business",       "http://rsshub:1200/reuters/category/businessNews"),
    ("Reuters Commodities",    "http://rsshub:1200/reuters/category/commoditiesNews"),
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

# 这些主机在部分环境有 SSL EOF 问题，单独关闭验证
_SSL_NO_VERIFY_HOSTS = {"feeds.reuters.com"}

# 最大并发 Feed 数（避免同时打开太多连接）
_FETCH_CONCURRENCY = 8


class RSSHubSource(BaseDataSource):
    """
    第一梯队黄金宏观情报 RSS 引擎。
    使用 DB 级批量去重，彻底替代原有的文件状态方案。
    使用 asyncio.gather() 并发抓取所有 Feed，大幅提升采集速度。
    """

    def __init__(self, db=None):
        super().__init__(db)
        self.feeds = TIER1_FEEDS
        self._semaphore: asyncio.Semaphore | None = None  # 延迟初始化，在事件循环内创建

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
    # 单 Feed 异步拉取（带重试 + SSL 回退）
    # ──────────────────────────────────────────────

    async def _fetch_feed_async(
        self,
        client: httpx.AsyncClient,
        ssl_client: httpx.AsyncClient,
        name: str,
        url: str,
    ) -> list[dict]:
        """
        异步拉取单个 RSS Feed，返回本 Feed 的新条目列表。
        - 最多重试 3 次，指数退避（1s / 2s / 4s）
        - 已知 SSL 问题主机（feeds.reuters.com）自动切换到 verify=False 重试
        """
        from urllib.parse import urlparse
        host = urlparse(url).hostname or ""
        # 已知 SSL 问题主机使用无验证客户端
        active_client = ssl_client if host in _SSL_NO_VERIFY_HOSTS else client

        async with self._semaphore:
            for attempt in range(3):
                try:
                    resp = await active_client.get(url, headers=_REQUEST_HEADERS)
                    break  # 成功，跳出重试循环
                except (httpx.ConnectError, httpx.RemoteProtocolError) as exc:
                    # 检查是否为 SSL 相关错误（兼容旧版 httpx 无 SSLError 属性的问题）
                    if "ssl" in str(exc).lower() and active_client is not ssl_client:
                        logger.warning(f"⚠️ [{name}] SSL 报错，切换无验证客户端重试: {exc}")
                        active_client = ssl_client
                        continue

                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    logger.warning(f"🔌 [{name}] 连接/SSL错误，跳过: {exc}")
                    return []
                except httpx.TimeoutException:
                    if attempt < 2:
                        await asyncio.sleep(2 ** attempt)
                        continue
                    logger.warning(f"⏱ [{name}] 超时，跳过")
                    return []
                except Exception as exc:
                    logger.error(f"❌ [{name}] 抓取异常: {exc}")
                    return []
            else:
                # for-else: 所有重试都进了 continue 但没 break
                return []

            if resp.status_code != 200:
                logger.warning(f"❌ [{name}] HTTP {resp.status_code}")
                return []

            # 解析 RSS（feedparser 是 CPU 操作，数据量小，直接调用）
            feed = feedparser.parse(resp.content)
            if not feed.entries:
                return []

            # DB 批量去重
            all_ids = [
                getattr(e, "id", None) or getattr(e, "link", None)
                for e in feed.entries
            ]
            all_ids = [i for i in all_ids if i]
            existing_ids = (
                self.db.source_ids_batch_exists(all_ids)
                if self.db else set()
            )

            # 内容过滤
            items = []
            for entry in feed.entries:
                item_id = getattr(entry, "id", None) or getattr(entry, "link", None)
                if not item_id or item_id in existing_ids:
                    continue

                title   = getattr(entry, "title",   "").strip()
                summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

                if not self._passes_filter(name, title, summary):
                    continue

                logger.info(f"🔥 [{name}] {title[:70]}...")
                items.append({
                    "source":    name,
                    "author":    name,
                    "timestamp": getattr(entry, "published", ""),
                    "content":   f"{title}. {summary}",
                    "url":       getattr(entry, "link", url),
                    "id":        item_id,
                })

            return items

    # ──────────────────────────────────────────────
    # 主抓取逻辑（异步并发版）
    # ──────────────────────────────────────────────

    async def fetch_async(self) -> list | None:
        """
        【推荐调用】并发拉取所有 Tier-1 RSS 信源。
        所有 Feed 同时发射 HTTP 请求，实际耗时 ≈ 最慢单个 Feed（约 15s）。
        原串行版本最坏耗时约 210s。
        """
        logger.info(f"🚀 并发扫描 {len(self.feeds)} 个 RSS 信源 (并发数: {_FETCH_CONCURRENCY})...")

        # 延迟初始化 Semaphore（确保在当前事件循环内创建）
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(_FETCH_CONCURRENCY)

        # 为所有 Feed 共享两个 AsyncClient（SSL 验证开/关各一个）
        client_settings = dict(
            timeout=httpx.Timeout(15.0),
            follow_redirects=True,
            limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
        )
        async with (
            httpx.AsyncClient(**client_settings, verify=True) as client,
            httpx.AsyncClient(**client_settings, verify=False) as ssl_client,
        ):
            tasks = [
                self._fetch_feed_async(client, ssl_client, name, url)
                for name, url in self.feeds
            ]
            # return_exceptions=True 确保单个 Feed 异常不影响其他 Feed
            results = await asyncio.gather(*tasks, return_exceptions=True)

        new_items = []
        for (name, _), result in zip(self.feeds, results):
            if isinstance(result, Exception):
                logger.error(f"❌ [{name}] gather 异常: {result}")
            elif result:
                new_items.extend(result)

        logger.info(
            f"✅ RSS 本轮完毕 | 并发采集 {len(self.feeds)} 个信源 | "
            f"黄金信号 {len(new_items)} 条 → AI 分析"
        )
        return new_items if new_items else None

    def fetch(self) -> list | None:
        """
        同步包装（向后兼容）。
        注意：若调用方已在 asyncio 事件循环内，应直接 await fetch_async() 以避免嵌套事件循环。
        """
        return asyncio.run(self.fetch_async())
