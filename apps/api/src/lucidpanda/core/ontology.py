from typing import Any

from src.lucidpanda.core.logger import logger
from src.lucidpanda.services.embedding_service import embedding_service

# ──────────────────────────────────────────────────────────────────────
# 1. 多级标签体系 (Taxonomy)
# 注入到 LLM 中，强制它在输出标签时，只能从这里的节点选择。
# ──────────────────────────────────────────────────────────────────────
TAXONOMY = {
    "AssetClass": ["Gold", "Equities_CN", "Equities_US", "FX_USD", "Treasures", "CrudeOil"],
    "MacroTheme": ["Geopolitics", "Monetary_Policy", "Inflation", "Economic_Growth", "Trade_War", "Fiscal_Policy"],
    "Sector": ["Technology", "Energy", "Financials", "RealEstate", "Semiconductors"]
}


# ──────────────────────────────────────────────────────────────────────
# 2. 核心大宗实体与别名注册表 (Core Entity Registry)
# 量化图谱的核心。包含量化交易最关注的宏观因素。
# 格式: { Canonical_ID: { "name": 标准名, "type": 实体类型, "aliases": [别名数组] } }
# ──────────────────────────────────────────────────────────────────────
CORE_ENTITIES = {
    # ── 央行与货币政策 ──
    "ent_fed": {
        "name": "Federal Reserve",
        "type": "CentralBank",
        "aliases": ["美联储", "联储", "FED", "FOMC", "美国联邦储备委员会"]
    },
    "ent_fed_powell": {
        "name": "Jerome Powell",
        "type": "Person",
        "aliases": ["鲍威尔", "杰罗姆·鲍威尔", "Powell", "Fed Chair", "美联储主席"]
    },
    "ent_pboc": {
        "name": "PBOC",
        "type": "CentralBank",
        "aliases": ["中国人民银行", "央行", "人行"]
    },
    
    # ── 宏观经济指标 ──
    "ent_us_cpi": {
        "name": "US CPI",
        "type": "MacroIndicator",
        "aliases": ["美国CPI", "CPI", "消费者物价指数", "核心CPI", "通胀数据"]
    },
    "ent_us_nfp": {
        "name": "US Nonfarm Payrolls",
        "type": "MacroIndicator",
        "aliases": ["非农", "美国非农就业", "NFP", "非农数据", "新增就业"]
    },

    # ── 地缘政治与核心人物 ──
    "ent_geo_mideast": {
        "name": "Middle East Conflict",
        "type": "Geopolitics",
        "aliases": ["中东局势", "中东冲突", "中东地区", "中东", "以哈冲突", "红海危机", "伊朗", "以色列", "巴以冲突"]
    },
    "ent_geo_rusukr": {
        "name": "Russia Ukraine War",
        "type": "Geopolitics",
        "aliases": ["俄乌战争", "俄乌冲突", "俄罗斯", "乌克兰"]
    },
    "ent_person_trump": {
        "name": "Donald Trump",
        "type": "Person",
        "aliases": ["特朗普", "唐纳德·特朗普", "Trump", "川普"]
    },
    "ent_person_biden": {
        "name": "Joe Biden",
        "type": "Person",
        "aliases": ["拜登", "乔·拜登", "Biden"]
    },

    # ── 核心资产 ──
    "ent_asset_gold": {
        "name": "Gold",
        "type": "Commodity",
        "aliases": ["黄金", "现货黄金", "金价", "XAU", "国际金价", "伦敦金"]
    },
    "ent_asset_usd": {
        "name": "US Dollar",
        "type": "Currency",
        "aliases": ["美元", "美元指数", "DXY", "美指", "USD"]
    },
    "ent_asset_us10y": {
        "name": "US 10Y Treasury",
        "type": "Bond",
        "aliases": ["美债十年期", "10年期美债收益率", "美债收益率", "US10Y", "十年期国债"]
    }
}


# ──────────────────────────────────────────────────────────────────────
# 3. 实体解析拦截器 (Entity Resolver)
# 负责在 AI 输出实体后，将非标文本强制替换/映射为 Canonical ID。
# ──────────────────────────────────────────────────────────────────────
class EntityResolver:
    """
    实体解析拦截器：将离散的新闻字符串统一对齐到 Core Entities。
    支持从数据库 (RegistryService) 动态加载。
    """
    def __init__(self, registry_service: Any | None = None):
        """
        初始化解析器。
        Args:
            registry_service: 实体注册服务。如果为 None，则加载硬编码的本地数据作为兜底。
        """
        self.registry_service = registry_service
        
        if self.registry_service:
            logger.info("🧠 EntityResolver: 已连接动态注册服务。")
        else:
            logger.warning("⚠️ EntityResolver: 未提供注册服务，使用硬编码内部数据。")
            # 内部构建一份别名映射以便兼容旧测试
            self._local_alias_map = {}
            for cid, data in CORE_ENTITIES.items():
                for alias in data.get("aliases", []):
                    self._local_alias_map[alias.lower()] = cid

    @property
    def alias_map(self) -> dict[str, str]:
        """按需获取当前的别名映射"""
        if self.registry_service:
            return self.registry_service.get_entity_mappings()
        return self._local_alias_map

    def resolve_name(self, raw_entity_name: str) -> str | None:
        """
        基于 raw string 解析出 canonical_id。
        """
        if not raw_entity_name:
            return None
            
        clean_name = str(raw_entity_name).strip().lower()
        current_map = self.alias_map
        
        # 1. 精确匹配 O(1)
        if clean_name in current_map:
            return current_map[clean_name]
            
        # 2. 包含匹配 (Sub-string)
        # 按照优先级（名字越长越具体，优先匹配长度长的词）
        sorted_aliases = sorted(current_map.keys(), key=len, reverse=True)
        for alias in sorted_aliases:
            if alias in clean_name:
                return current_map[alias]
                
        # 3. 向量化兜底匹配 (如果存在 registry_service)
        if self.registry_service:
            try:
                vec = embedding_service.encode(clean_name)
                canonical_id = self.registry_service.find_closest_entity(vec)
                if canonical_id:
                    logger.debug(f"🧲 向量兜底命中: [{clean_name}] -> {canonical_id}")
                    return canonical_id
            except Exception as e:
                logger.warning(f"⚠️ 实体兜底向量化处理失败 [{clean_name}]: {e}")

        # 4. 未匹配到
        return None

    def process_ai_entities(self, raw_entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        处理 AI 产生的 Entities 数组，注入 canonical_id 字段。
        """
        if not raw_entities:
            return []
            
        processed = []
        for ent in raw_entities:
            new_ent = dict(ent)
            raw_name = new_ent.get("name", "")
            
            canonical_id = self.resolve_name(raw_name)
            if canonical_id:
                new_ent["canonical_id"] = canonical_id
                logger.debug(f"🔗 实体对齐成功: [{raw_name}] -> {canonical_id}")
            else:
                new_ent["canonical_id"] = None
                
            processed.append(new_ent)
            
        return processed

# 延迟加载解析器单例，避免导入时触发未初始化的警告
_default_resolver = None

def get_default_resolver():
    """获取默认解析器单例（按需初始化）"""
    global _default_resolver
    if _default_resolver is None:
        _default_resolver = EntityResolver()
    return _default_resolver
