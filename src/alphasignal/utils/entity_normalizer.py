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
