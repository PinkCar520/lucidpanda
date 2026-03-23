"""
依赖注入容器

用于管理 AlphaEngine 的所有依赖，实现：
1. 依赖解耦
2. 单元测试友好
3. 按需初始化（节省内存）
4. 配置集中管理
"""
import asyncio
from typing import List, Optional, TYPE_CHECKING

from src.lucidpanda.config import settings
from src.lucidpanda.core.database import IntelligenceDB
from src.lucidpanda.core.backtest import BacktestEngine
from src.lucidpanda.core.event_clusterer import EventClusterer
from src.lucidpanda.core.deduplication import NewsDeduplicator
from src.lucidpanda.providers.channels.email import EmailChannel
from src.lucidpanda.providers.channels.bark import BarkChannel
from src.lucidpanda.services.agent_tools import list_tool_summaries
from src.lucidpanda.core.ontology import EntityResolver
from src.lucidpanda.services.factor_service import FactorService

# 避免循环导入
if TYPE_CHECKING:
    from src.lucidpanda.core.engine import LLMFactory


class EngineDependencies:
    """
    AlphaEngine 依赖容器
    
    按需初始化依赖，避免不必要的内存占用。
    支持延迟加载（lazy loading）。
    
    Attributes:
        db: 数据库连接（立即初始化）
        backtester: 回测引擎（延迟初始化）
        clusterer: 事件聚类器（延迟初始化）
        deduplicator: 去重引擎（延迟初始化）
        channels: 通知渠道列表（延迟初始化）
        tool_summaries: 工具摘要（延迟初始化）
        entity_resolver: 实体解析器（延迟初始化）
        ai_semaphore: 并发控制信号量（立即初始化）
    """
    
    def __init__(
        self,
        db: Optional[IntelligenceDB] = None,
        llm_provider: Optional[str] = None,
        fallback_provider: Optional[str] = None,
    ):
        """
        初始化依赖容器
        
        Args:
            db: 数据库实例（可选，默认自动创建）
            llm_provider: 主力 LLM 提供商（可选，默认从配置读取）
            fallback_provider: 备用 LLM 提供商（可选，默认从配置读取）
        """
        # 立即初始化：数据库和信号量
        self._db = db
        self._llm_provider = llm_provider
        self._fallback_provider = fallback_provider
        
        # 并发控制（立即初始化）
        self.ai_semaphore = asyncio.Semaphore(settings.LLM_CONCURRENCY_LIMIT)
        
        # 延迟初始化：其他组件
        self._backtester: Optional[BacktestEngine] = None
        self._clusterer: Optional[EventClusterer] = None
        self._deduplicator: Optional[NewsDeduplicator] = None
        self._channels: Optional[List] = None
        self._tool_summaries: Optional[List] = None
        self._entity_resolver: Optional[EntityResolver] = None
        self._factor_service: Optional[FactorService] = None
        self._ontology_repo: Optional[Any] = None
        self._registry_service: Optional[Any] = None
        self._primary_llm = None
        self._fallback_llm = None
    
    @property
    def db(self) -> IntelligenceDB:
        """数据库实例（单例）"""
        if self._db is None:
            self._db = IntelligenceDB()
        return self._db
    
    @property
    def primary_llm(self):
        """主力 LLM 实例（单例）"""
        if self._primary_llm is None:
            # 延迟导入，避免循环依赖
            from src.lucidpanda.core.engine import LLMFactory
            provider = self._llm_provider or settings.AI_PROVIDER.lower()
            self._primary_llm = LLMFactory.create(provider)
        return self._primary_llm
    
    @property
    def fallback_llm(self):
        """备用 LLM 实例（单例）"""
        if self._fallback_llm is None:
            # 延迟导入，避免循环依赖
            from src.lucidpanda.core.engine import LLMFactory
            provider = self._fallback_provider or LLMFactory.get_fallback_provider(
                self._llm_provider or settings.AI_PROVIDER.lower()
            )
            self._fallback_llm = LLMFactory.create(provider)
        return self._fallback_llm
    
    @property
    def backtester(self) -> BacktestEngine:
        """回测引擎（延迟初始化）"""
        if self._backtester is None:
            self._backtester = BacktestEngine(self.db)
        return self._backtester
    
    @property
    def clusterer(self) -> EventClusterer:
        """事件聚类器（延迟初始化）"""
        if self._clusterer is None:
            self._clusterer = EventClusterer(db=self.db)
        return self._clusterer
    
    @property
    def deduplicator(self) -> NewsDeduplicator:
        """去重引擎（延迟初始化）"""
        if self._deduplicator is None:
            self._deduplicator = NewsDeduplicator(db=self.db)
        return self._deduplicator
    
    @property
    def channels(self) -> List:
        """通知渠道列表（延迟初始化）"""
        if self._channels is None:
            self._channels = [EmailChannel(), BarkChannel()]
        return self._channels
    
    @property
    def tool_summaries(self) -> List:
        """工具摘要（延迟初始化）"""
        if self._tool_summaries is None:
            self._tool_summaries = list_tool_summaries()
        return self._tool_summaries
    
    @property
    def ontology_repo(self) -> Any:
        """本体元数据仓库"""
        if self._ontology_repo is None:
            from src.lucidpanda.db.ontology_repo import OntologyRepo
            self._ontology_repo = OntologyRepo()
        return self._ontology_repo

    @property
    def registry_service(self) -> Any:
        """实体注册动态加载服务"""
        if self._registry_service is None:
            from src.lucidpanda.services.registry_service import RegistryService
            self._registry_service = RegistryService(self.ontology_repo)
        return self._registry_service

    @property
    def entity_resolver(self) -> EntityResolver:
        """实体解析拦截管线（延迟初始化）"""
        if self._entity_resolver is None:
            self._entity_resolver = EntityResolver(self.registry_service)
        return self._entity_resolver
        
    @property
    def factor_service(self) -> FactorService:
        """实体舆情因子聚合服务（延迟初始化）"""
        if self._factor_service is None:
            self._factor_service = FactorService()
        return self._factor_service
    
    @property
    def enable_agent_tools(self) -> bool:
        """是否启用 Agent 工具"""
        return settings.ENABLE_AGENT_TOOLS
    
    def clear_cache(self):
        """
        清理缓存的依赖实例
        
        用于测试或重新加载配置。
        注意：不会清理数据库连接。
        """
        self._backtester = None
        self._clusterer = None
        self._deduplicator = None
        self._channels = None
        self._tool_summaries = None
        self._entity_resolver = None
        self._factor_service = None
        self._ontology_repo = None
        self._registry_service = None
        self._primary_llm = None
        self._fallback_llm = None
