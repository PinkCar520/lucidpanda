import re
import unicodedata

ALIAS_MAP = {
    # 人物
    "donald trump": "Trump",
    "trump": "Trump",
    "特朗普": "Trump",
    "jerome powell": "Powell",
    "powell": "Powell",
    "鲍威尔": "Powell",
    "janet yellen": "Yellen",
    "yellen": "Yellen",
    "耶伦": "Yellen",
    # 机构
    "federal reserve": "Fed",
    "fed": "Fed",
    "美联储": "Fed",
    "fomc": "Fed",
    "european central bank": "ECB",
    "ecb": "ECB",
    "欧洲央行": "ECB",
    "people's bank of china": "PBOC",
    "peoples bank of china": "PBOC",
    "pboc": "PBOC",
    "中国人民银行": "PBOC",
    "bank of england": "BOE",
    "boe": "BOE",
    "英格兰银行": "BOE",
    "bank of japan": "BOJ",
    "boj": "BOJ",
    "日本银行": "BOJ",
    # 资产
    "gold": "Gold",
    "黄金": "Gold",
    "xau": "Gold",
    "xauusd": "Gold",
    "wti": "Oil",
    "crude oil": "Oil",
    "oil": "Oil",
    "原油": "Oil",
    "brent": "Brent",
    "布伦特": "Brent",
    "us dollar": "USD",
    "usd": "USD",
    "美元": "USD",
    "dxy": "DXY",
    "dollar index": "DXY",
    "us10y": "US10Y",
    "10-year treasury": "US10Y",
    "ten year treasury": "US10Y",
    "美债": "US10Y",
    "bitcoin": "Bitcoin",
    "btc": "Bitcoin",
    "比特币": "Bitcoin",
    # 政策/事件
    "tariff": "Tariff",
    "关税": "Tariff",
    "trade war": "TradeWar",
    "贸易战": "TradeWar",
    # A股指数与宽基
    "沪深300": "CSI300",
    "csi 300": "CSI300",
    "hs300": "CSI300",
    "中证500": "CSI500",
    "csi 500": "CSI500",
    "zz500": "CSI500",
    "上证50": "SSE50",
    "sz50": "SSE50",
    "创业板": "Chinext",
    "chinext": "Chinext",
    "科创50": "Star50",
    "star50": "Star50",
    "恒生指数": "HSI",
    "hsi": "HSI",
    "hang seng": "HSI",
}

# 规范化实体类型：已知实体的官方 type（优先级高于 LLM 输出）
CANONICAL_TYPE_MAP = {
    "trump": "person",
    "powell": "person",
    "yellen": "person",
    "xi": "person",
    "gold": "commodity",
    "oil": "commodity",
    "brent": "commodity",
    "usd": "currency",
    "dxy": "index",
    "us10y": "bond",
    "bitcoin": "crypto",
    "fed": "organization",
    "ecb": "organization",
    "pboc": "organization",
    "boe": "organization",
    "boj": "organization",
    "tariff": "policy",
    "tradewar": "event",
    "csi300": "index",
    "csi500": "index",
    "sse50": "index",
    "chinext": "index",
    "star50": "index",
    "hsi": "index",
}


def _canonical_key(name: str) -> str:
    text = unicodedata.normalize("NFKC", (name or "").strip())
    text = text.replace("\u2019", "'")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def normalize_entity_name(name: str) -> str:
    """将实体名称归一化为标准形式（解决别名碎片化）。"""
    clean_name = (name or "").strip()
    if not clean_name:
        return ""
    canonical_key = _canonical_key(clean_name)
    return ALIAS_MAP.get(canonical_key, clean_name)


def normalize_fund_name(name: str) -> str:
    """
    针对 A 股基金名称的特殊预处理。
    去除：联接A/C, 混合, ETF, 增强, 行业/主题等冗余后缀。
    目的是提取核心投资标的（如：沪深300、半导体、白酒）。
    """
    if not name:
        return ""
    # 1. 移除括号及其内容 (如: 华夏沪深300(QDII))
    name = re.sub(r"\(.*?\)|（.*?）", "", name)
    # 2. 移除常见后缀 (按顺序尝试，最长匹配优先)
    suffixes = [
        r"联接[ABCDEI]$", r"混合[ABCDEI]$", r"债券[ABCDEI]$",
        r"联接$", r"混合$", r"精选$", r"增强$", r"ETF$", r"LOF$",
        r"主题$", r"核心$", r"优选$", r"价值$", r"成长$", r"量化$"
    ]
    for pattern in suffixes:
        name = re.sub(pattern, "", name)
    
    # 3. 移除基金公司前缀 (常见的大型基金公司)
    companies = ["华夏", "易方达", "广发", "富国", "汇添富", "南方", "嘉实", "博时", "招商", "工银瑞信"]
    for co in companies:
        if name.startswith(co) and len(name) > len(co) + 2: # 避免把 "华夏成长" 误杀成 "成长"
            name = name[len(co):]
            
    return name.strip()


def normalize_entity_type(name: str, llm_type: str) -> str:
    """
    返回实体的规范化类型。
    对于已知实体（Gold/Trump/Fed 等），忽略 LLM 输出的 'unknown'，
    始终使用预定义的 CANONICAL_TYPE_MAP 中的官方类型，
    防止同一实体因类型不同产生多个节点。
    """
    canonical_name = normalize_entity_name(name)
    canonical_key = canonical_name.strip().lower()
    if canonical_key in CANONICAL_TYPE_MAP:
        return CANONICAL_TYPE_MAP[canonical_key]
    # 未知实体：LLM 给的类型如果是 unknown，则尝试从 normalized_name 查一次
    if llm_type and llm_type.strip().lower() not in ("unknown", "other", ""):
        return llm_type.strip().lower()
    return "unknown"
