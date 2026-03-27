"""
Pydantic 配置验证测试
"""

import pytest

from src.lucidpanda.config.pydantic_settings import (
    EmbeddingSettings,
    LLMSettings,
    Settings,
)


class TestLLMSettings:
    """LLM 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        llm = LLMSettings()
        assert llm.ai_provider == "qwen"
        assert llm.llm_fallback_order == ["qwen", "deepseek", "gemini"]
        assert llm.qwen_model == "qwen3.5-flash"

    def test_invalid_fallback_order(self):
        """测试无效降级顺序"""
        with pytest.raises(ValueError, match="无效的 LLM 提供商"):
            LLMSettings(llm_fallback_order=["invalid", "provider"])

    def test_custom_fallback_order(self):
        """测试自定义降级顺序"""
        llm = LLMSettings(llm_fallback_order=["deepseek", "qwen"])
        assert llm.llm_fallback_order == ["deepseek", "qwen"]


class TestEmbeddingSettings:
    """Embedding 配置测试"""

    def test_default_values(self):
        """测试默认值"""
        emb = EmbeddingSettings()
        assert emb.embedding_provider == "dashscope"
        assert emb.dashscope_embedding_model == "text-embedding-v3"
        assert emb.dashscope_embedding_dimensions == 768

    def test_valid_dimensions(self):
        """测试有效维度"""
        for dim in [64, 128, 256, 512, 768, 1024, 1536]:
            emb = EmbeddingSettings(dashscope_embedding_dimensions=dim)
            assert emb.dashscope_embedding_dimensions == dim

    def test_invalid_dimensions(self):
        """测试无效维度"""
        with pytest.raises(ValueError, match="无效的维度"):
            EmbeddingSettings(dashscope_embedding_dimensions=999)


class TestSettings:
    """完整配置测试"""

    def test_settings_from_env(self):
        """测试从环境变量加载配置"""
        import os

        os.environ["AI_PROVIDER"] = "deepseek"
        os.environ["LLM_CONCURRENCY_LIMIT"] = "10"

        settings = Settings()
        assert settings.AI_PROVIDER == "deepseek"
        assert settings.LLM_CONCURRENCY_LIMIT == 10

        # 清理
        del os.environ["AI_PROVIDER"]
        del os.environ["LLM_CONCURRENCY_LIMIT"]

    def test_settings_shortcut_properties(self):
        """测试快捷访问属性"""
        settings = Settings()

        # 测试 LLM 相关
        assert hasattr(settings, "QWEN_API_KEY")
        assert hasattr(settings, "QWEN_MODEL")
        assert hasattr(settings, "LLM_FALLBACK_ORDER")

        # 测试 Embedding 相关
        assert hasattr(settings, "DASHSCOPE_API_KEY")
        assert hasattr(settings, "DASHSCOPE_EMBEDDING_MODEL")

        # 测试运行时
        assert hasattr(settings, "LLM_CONCURRENCY_LIMIT")
        assert hasattr(settings, "AGENT_TOOL_MAX_CALLS")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
