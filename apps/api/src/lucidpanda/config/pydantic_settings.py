"""
Pydantic 配置验证

使用 Pydantic Settings 进行配置验证，提供：
1. 类型安全
2. 自动验证
3. 清晰的错误信息
4. IDE 自动补全
"""

import os

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseModel):
    """LLM 相关配置"""

    ai_provider: str = Field(default="qwen", description="主力 AI 提供商")
    llm_fallback_order: list[str] = Field(
        default=["qwen", "deepseek", "gemini"], description="LLM 降级顺序"
    )

    # Qwen
    qwen_api_key: str | None = Field(default=None, description="Qwen API Key")
    qwen_model: str = Field(default="qwen3.5-flash", description="Qwen 模型")
    qwen_base_url: str = Field(
        default="https://dashscope.aliyuncs.com/compatible-mode/v1",
        description="Qwen API 基础 URL",
    )

    # Gemini
    gemini_api_key: str | None = Field(default=None, description="Gemini API Key")
    gemini_model: str = Field(default="gemini-2.5-flash", description="Gemini 模型")
    gemini_batch_model: str = Field(default="gemini-2.0-flash-lite")
    gemini_embedding_model: str = Field(default="models/gemini-embedding-001")

    # DeepSeek
    deepseek_api_key: str | None = Field(default=None)
    deepseek_base_url: str = Field(default="https://api.deepseek.com")
    deepseek_model: str = Field(default="deepseek-chat")

    @field_validator("llm_fallback_order")
    @classmethod
    def validate_fallback_order(cls, v):
        """验证降级顺序"""
        valid_providers = {"qwen", "deepseek", "gemini"}
        for provider in v:
            if provider not in valid_providers:
                raise ValueError(
                    f"无效的 LLM 提供商：{provider}，可选值：{valid_providers}"
                )
        return v


class EmbeddingSettings(BaseModel):
    """Embedding 相关配置"""

    embedding_provider: str = Field(default="dashscope")

    # DashScope
    dashscope_api_key: str | None = Field(default=None)
    dashscope_embedding_model: str = Field(default="text-embedding-v3")
    dashscope_embedding_dimensions: int = Field(default=768, ge=64, le=2048)

    @field_validator("dashscope_embedding_dimensions")
    @classmethod
    def validate_dimensions(cls, v):
        """验证维度"""
        valid_dimensions = {64, 128, 256, 512, 768, 1024, 1536, 2048}
        if v not in valid_dimensions:
            raise ValueError(f"无效的维度：{v}，可选值：{valid_dimensions}")
        return v


class RuntimeSettings(BaseModel):
    """运行时配置"""

    llm_concurrency_limit: int = Field(default=5, ge=1, le=50)
    agent_tool_max_calls: int = Field(default=3, ge=1, le=10)
    agent_tool_timeout_seconds: int = Field(default=8, ge=1, le=60)
    enable_agent_tools: bool = Field(default=True)
    enable_semantic_dedupe: bool = Field(default=True)


class DatabaseSettings(BaseModel):
    """数据库配置"""

    db_type: str = Field(default="postgres")
    postgres_user: str = Field(default="postgres")
    postgres_password: str = Field(default="postgres")
    postgres_host: str = Field(default="localhost")
    postgres_port: int = Field(default=5432)
    postgres_db: str = Field(default="lucidpanda")


class Settings(BaseSettings):
    """
    统一配置类

    所有配置从环境变量加载，提供类型安全和自动验证。

    Example:
        settings = Settings()
        print(settings.AI_PROVIDER)  # qwen
        print(settings.LLM_CONCURRENCY_LIMIT)  # 5
    """

    model_config = SettingsConfigDict(
        env_file=[".env", ".env.ai"],
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # 忽略未定义的字段
    )

    # 基础配置
    simulation_mode: bool = Field(default=False)
    check_interval_minutes: int = Field(default=2)

    # 子配置
    llm: LLMSettings = Field(default_factory=LLMSettings)
    embedding: EmbeddingSettings = Field(default_factory=EmbeddingSettings)
    runtime: RuntimeSettings = Field(default_factory=RuntimeSettings)
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)

    def model_post_init(self, __context) -> None:
        """支持旧版平铺环境变量，兼容现有测试和调用方。"""
        ai_provider = os.getenv("AI_PROVIDER")
        if ai_provider:
            self.llm.ai_provider = ai_provider

        llm_concurrency_limit = os.getenv("LLM_CONCURRENCY_LIMIT")
        if llm_concurrency_limit:
            self.runtime.llm_concurrency_limit = int(llm_concurrency_limit)

    # 快捷访问（兼容旧代码）
    @property
    def AI_PROVIDER(self) -> str:
        return self.llm.ai_provider

    @property
    def LLM_FALLBACK_ORDER(self) -> list[str]:
        return self.llm.llm_fallback_order

    @property
    def LLM_CONCURRENCY_LIMIT(self) -> int:
        return self.runtime.llm_concurrency_limit

    @property
    def AGENT_TOOL_MAX_CALLS(self) -> int:
        return self.runtime.agent_tool_max_calls

    @property
    def AGENT_TOOL_TIMEOUT_SECONDS(self) -> int:
        return self.runtime.agent_tool_timeout_seconds

    @property
    def ENABLE_AGENT_TOOLS(self) -> bool:
        return self.runtime.enable_agent_tools

    @property
    def ENABLE_SEMANTIC_DEDUPE(self) -> bool:
        return self.runtime.enable_semantic_dedupe

    @property
    def QWEN_API_KEY(self) -> str | None:
        return self.llm.qwen_api_key

    @property
    def QWEN_MODEL(self) -> str:
        return self.llm.qwen_model

    @property
    def QWEN_BASE_URL(self) -> str:
        return self.llm.qwen_base_url

    @property
    def GEMINI_API_KEY(self) -> str | None:
        return self.llm.gemini_api_key

    @property
    def GEMINI_MODEL(self) -> str:
        return self.llm.gemini_model

    @property
    def DEEPSEEK_API_KEY(self) -> str | None:
        return self.llm.deepseek_api_key

    @property
    def DEEPSEEK_MODEL(self) -> str:
        return self.llm.deepseek_model

    @property
    def DEEPSEEK_BASE_URL(self) -> str:
        return self.llm.deepseek_base_url

    @property
    def DASHSCOPE_API_KEY(self) -> str | None:
        return self.embedding.dashscope_api_key

    @property
    def DASHSCOPE_EMBEDDING_MODEL(self) -> str:
        return self.embedding.dashscope_embedding_model

    @property
    def DASHSCOPE_EMBEDDING_DIMENSIONS(self) -> int:
        return self.embedding.dashscope_embedding_dimensions

    @property
    def POSTGRES_USER(self) -> str:
        return self.database.postgres_user

    @property
    def POSTGRES_PASSWORD(self) -> str:
        return self.database.postgres_password

    @property
    def POSTGRES_HOST(self) -> str:
        return self.database.postgres_host

    @property
    def POSTGRES_PORT(self) -> int:
        return self.database.postgres_port

    @property
    def POSTGRES_DB(self) -> str:
        return self.database.postgres_db


# 单例实例
_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


# 兼容旧代码
settings = get_settings()
