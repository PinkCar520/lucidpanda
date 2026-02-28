"""
AlphaSignal RSS Intelligence Source
=====================================
第一梯队极速宏观情报引擎，直接对接各大权威媒体的官方 RSS Feed。

架构设计原则：
1. 零中间层：绕过 rsshub.app 公共节点，直连媒体官方 Feed（更稳定、更低延迟）
2. 精准聚焦：所有信源均围绕黄金价格的宏观驱动因子选取
3. 三级过滤：
   - 去重层：跳过已处理的 item_id（state 文件缓存）
   - 噪音层：噪音关键词黑名单，直接拦截明显无关内容
   - 信号层：按信源类型分别应用不同严格程度的相关性过滤
4. 所有 Feed URL 均经过实际 HTTP 200 + RSS 格式验证（2026-02-28）
"""

import json
import os
import requests
import feedparser
from src.alphasignal.config import settings
from src.alphasignal.core.logger import logger
from src.alphasignal.providers.data_sources.base import BaseDataSource


# ──────────────────────────────────────────────
# RSS 信源配置
# 格式：(显示名称, RSS URL)
# ──────────────────────────────────────────────
TIER1_FEEDS = [
    # ── 政治风险层（黄金最直接的驱动力）────────────────────────────────
    # Trump 原文帖子，经实测可访问（trumpstruth.org 替代失效的 rsshub.app 节点）
    ("Trump Truth Social",    "https://www.trumpstruth.org/feed"),
    # 白宫官方行政命令 & 总统备忘录（政策风险的原始一手来源）
    ("WhiteHouse Exec Orders","https://www.whitehouse.gov/presidential-actions/feed/"),

    # ── 彭博社 Bloomberg ─────────────────────────────────────────────
    ("Bloomberg Markets",     "https://feeds.bloomberg.com/markets/news.rss"),
    ("Bloomberg Economics",   "https://feeds.bloomberg.com/economics/news.rss"),
    ("Bloomberg Top News",    "https://feeds.bloomberg.com/bview/news.rss"),

    # ── 华尔街日报 WSJ ───────────────────────────────────────────────
    ("WSJ Markets",           "https://feeds.a.dj.com/rss/RSSMarketsMain.xml"),
    ("WSJ Economy",           "https://feeds.a.dj.com/rss/WSJcomUSBusiness.xml"),
    ("WSJ Full (feedx)",      "https://feedx.net/rss/wsj.xml"),

    # ── 纽约时报 NYT ─────────────────────────────────────────────────
    ("NYT Top News",          "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"),

    # ── CNBC ────────────────────────────────────────────────────────
    ("CNBC Top News",         "https://www.cnbc.com/id/100003114/device/rss/rss.html"),
    ("CNBC Finance",          "https://www.cnbc.com/id/10000664/device/rss/rss.html"),
    ("CNBC Economy",          "https://www.cnbc.com/id/20910258/device/rss/rss.html"),

    # ── 金融时报 FT ──────────────────────────────────────────────────
    ("Financial Times",       "https://www.ft.com/?format=rss"),

    # ── 路透社 Reuters（本地 SSL 问题，腾讯云服务器上正常）────────────────
    ("Reuters Top News",      "https://feeds.reuters.com/reuters/topNews"),
    ("Reuters Business",      "https://feeds.reuters.com/reuters/businessNews"),
    ("Reuters Commodities",   "https://feeds.reuters.com/reuters/commoditiesNews"),
]

# ──────────────────────────────────────────────
# 过滤关键词配置
# ──────────────────────────────────────────────

# 噪音黑名单：命中任意一词 → 直接拦截（优先级最高）
_NOISE_KEYWORDS = frozenset([
    "nfl", "nba", "soccer", "olympic", "grammy", "oscar",
    "celebrity", "recipe", "fashion", "lifestyle", "dating",
    "relationship", "epstein", "clinton scandal", "reality tv",
])

# 黄金宏观驱动关键词：命中任意一词 → 视为相关（通用信源使用）
_GOLD_RELEVANCE_KEYWORDS = frozenset([
    # 黄金本身
    "gold", "xau", "silver", "precious metal", "bullion",
    "spot price", "comex", "lbma",
    # 特朗普政策（非 Truth Social 信源中提及 Trump 必然是政策报道）
    "trump", "white house", "executive order", "mar-a-lago",
    "administration", "tariff",
    # 美联储 & 货币政策
    "federal reserve", "fed ", "fomc", "interest rate",
    "rate cut", "rate hike", "powell", "monetary policy",
    "quantitative", "balance sheet",
    # 通胀 & 宏观数据
    "inflation", "cpi", "pce", "deflation", "stagflation",
    "gdp", "recession", "jobs report", "nonfarm", "unemployment",
    # 美元 & 债券（与黄金强负相关）
    "dollar", "dxy", "treasury", "yield", "bond",
    "10-year", "debt", "currency", "forex", "fx ",
    # 地缘政治风险
    "geopolit", "war", "conflict", "sanction", "iran",
    "russia", "ukraine", "middle east", "oil", "opec", "energy crisis",
    # 系统性金融风险
    "safe haven", "crisis", "crash", "collapse", "bank run",
    "systemic", "contagion", "liquidity", "credit risk",
    # 贸易战 & 关税
    "trade war", "trade deal", "import tax",
])

# Trump Truth Social 二次严格过滤：必须同时含有宏观/地缘/市场关键词才放行
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
    """第一梯队黄金宏观情报 RSS 引擎（直连官方 Feed，带三级过滤）。"""

    def __init__(self):
        self.processed_ids = self._load_state()
        self.feeds = TIER1_FEEDS

    # ──────────────────────────────────────────────
    # 过滤器
    # ──────────────────────────────────────────────

    def _is_noise(self, text: str) -> bool:
        """黑名单噪音检测。"""
        return any(kw in text for kw in _NOISE_KEYWORDS)

    def _is_gold_relevant(self, text: str) -> bool:
        """通用黄金宏观相关性检测（彭博/CNBC/WSJ 等使用）。"""
        return any(kw in text for kw in _GOLD_RELEVANCE_KEYWORDS)

    def _is_trump_macro(self, text: str) -> bool:
        """Trump Truth Social 专用的严格二次过滤（排除背书/娱乐帖）。"""
        return any(kw in text for kw in _TRUMP_MACRO_KEYWORDS)

    def _passes_filter(self, source_name: str, title: str, summary: str) -> bool:
        """统一过滤入口，按信源类型选择对应的过滤策略。"""
        text = f"{title} {summary}".lower()
        if self._is_noise(text):
            return False
        if source_name == "Trump Truth Social":
            return self._is_trump_macro(text)     # 严格策略
        return self._is_gold_relevant(text)        # 通用策略

    # ──────────────────────────────────────────────
    # 主抓取逻辑
    # ──────────────────────────────────────────────

    def fetch(self) -> list | None:
        """
        遍历所有 Tier-1 RSS 信源，经三级过滤后返回黄金相关情报列表。
        Returns:
            list[dict] 若有新情报，否则 None。
        """
        new_items = []
        total_fetched = 0
        total_filtered = 0

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

                for entry in feed.entries:
                    item_id = getattr(entry, "id", None) or getattr(entry, "link", None)
                    if not item_id or item_id in self.processed_ids:
                        continue

                    title   = getattr(entry, "title",   "").strip()
                    summary = getattr(entry, "summary", "") or getattr(entry, "description", "")
                    total_fetched += 1

                    if not self._passes_filter(name, title, summary):
                        total_filtered += 1
                        self._save_state(item_id)   # 标记为已读，下次不重复判断
                        continue

                    logger.info(f"🔥 [{name}] {title[:70]}...")
                    self._save_state(item_id)
                    new_items.append({
                        "source":    name,
                        "author":    "System",
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
            f"✅ 本轮完毕 | 读取 {total_fetched} 条 | "
            f"过滤 {total_filtered} 条 | "
            f"黄金信号 {len(new_items)} 条 → AI 分析"
        )
        return new_items if new_items else None

    # ──────────────────────────────────────────────
    # 状态持久化（去重缓存）
    # ──────────────────────────────────────────────

    def _load_state(self) -> set:
        if os.path.exists(settings.STATE_FILE):
            try:
                with open(settings.STATE_FILE, "r") as f:
                    return set(json.load(f))
            except Exception:
                pass
        return set()

    def _save_state(self, new_id: str) -> None:
        self.processed_ids.add(new_id)
        if len(self.processed_ids) > 2000:
            self.processed_ids = set(list(self.processed_ids)[-2000:])
        with open(settings.STATE_FILE, "w") as f:
            json.dump(list(self.processed_ids), f)
