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
    # 资产
    "gold": "Gold",
    "黄金": "Gold",
    "xau": "Gold",
    "xauusd": "Gold",
    "wti": "Oil",
    "crude oil": "Oil",
    "oil": "Oil",
    "原油": "Oil",
    "us dollar": "USD",
    "usd": "USD",
    "美元": "USD",
}


def _canonical_key(name: str) -> str:
    text = unicodedata.normalize("NFKC", (name or "").strip())
    text = text.replace("’", "'")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def normalize_entity_name(name: str) -> str:
    clean_name = (name or "").strip()
    if not clean_name:
        return ""
    canonical_key = _canonical_key(clean_name)
    return ALIAS_MAP.get(canonical_key, clean_name)
