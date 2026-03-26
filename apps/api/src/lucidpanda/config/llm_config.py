"""
LLM 提供商配置模块
统一管理所有 LLM 提供商的配置信息
"""
from dataclasses import dataclass


@dataclass
class LLMProviderConfig:
    """LLM 提供商配置"""
    name: str
    api_key: str | None = None
    model: str | None = None
    base_url: str | None = None
    enabled: bool = True


@dataclass
class EmbeddingProviderConfig:
    """Embedding 提供商配置"""
    name: str
    api_key: str | None = None
    model: str | None = None
    dimensions: int = 768
    enabled: bool = True


class LLMConfigManager:
    """
    LLM 配置管理器
    提供统一的配置访问接口
    """

    # 支持的 LLM 提供商
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    QWEN = "qwen"

    # 支持的 Embedding 提供商
    DASHSCOPE = "dashscope"
    GEMINI_EMBEDDING = "gemini"

    @staticmethod
    def get_llm_providers() -> dict[str, LLMProviderConfig]:
        """获取所有 LLM 提供商配置"""
        from src.lucidpanda.config import settings

        return {
            LLMConfigManager.GEMINI: LLMProviderConfig(
                name=LLMConfigManager.GEMINI,
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_MODEL,
                base_url=None,  # Gemini 使用 SDK 默认 URL
                enabled=bool(settings.GEMINI_API_KEY)
            ),
            LLMConfigManager.DEEPSEEK: LLMProviderConfig(
                name=LLMConfigManager.DEEPSEEK,
                api_key=settings.DEEPSEEK_API_KEY,
                model=settings.DEEPSEEK_MODEL,
                base_url=settings.DEEPSEEK_BASE_URL,
                enabled=bool(settings.DEEPSEEK_API_KEY)
            ),
            LLMConfigManager.QWEN: LLMProviderConfig(
                name=LLMConfigManager.QWEN,
                api_key=settings.QWEN_API_KEY,
                model=settings.QWEN_MODEL,
                base_url=settings.QWEN_BASE_URL,
                enabled=bool(settings.QWEN_API_KEY)
            ),
        }

    @staticmethod
    def get_embedding_providers() -> dict[str, EmbeddingProviderConfig]:
        """获取所有 Embedding 提供商配置"""
        from src.lucidpanda.config import settings

        return {
            LLMConfigManager.DASHSCOPE: EmbeddingProviderConfig(
                name=LLMConfigManager.DASHSCOPE,
                api_key=settings.DASHSCOPE_API_KEY,
                model=settings.DASHSCOPE_EMBEDDING_MODEL,
                dimensions=settings.DASHSCOPE_EMBEDDING_DIMENSIONS,
                enabled=bool(settings.DASHSCOPE_API_KEY)
            ),
            LLMConfigManager.GEMINI_EMBEDDING: EmbeddingProviderConfig(
                name=LLMConfigManager.GEMINI_EMBEDDING,
                api_key=settings.GEMINI_API_KEY,
                model=settings.GEMINI_EMBEDDING_MODEL,
                dimensions=768,
                enabled=bool(settings.GEMINI_API_KEY)
            ),
        }

    @staticmethod
    def get_active_llm(provider_name:
        str) -> LLMProviderConfig:
        """获取指定 LLM 提供商配置"""
        providers = LLMConfigManager.get_llm_providers()
        if provider_name not in providers:
            raise ValueError(f"未知的 LLM 提供商：{provider_name}")
        return providers[provider_name]

    @staticmethod
    def get_active_embedding(provider_name:
        str) -> EmbeddingProviderConfig:
        """获取指定 Embedding 提供商配置"""
        providers = LLMConfigManager.get_embedding_providers()
        if provider_name not in providers:
            raise ValueError(f"未知的 Embedding 提供商：{provider_name}")
        return providers[provider_name]

    @staticmethod
    def get_available_llms() -> list[str]:
        """获取可用的 LLM 提供商列表"""
        providers = LLMConfigManager.get_llm_providers()
        return [name for name, config in providers.items() if config.enabled]

    @staticmethod
    def get_available_embeddings() -> list[str]:
        """获取可用的 Embedding 提供商列表"""
        providers = LLMConfigManager.get_embedding_providers()
        return [name for name, config in providers.items() if config.enabled]
