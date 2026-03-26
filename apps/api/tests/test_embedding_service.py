"""
Embedding Service 单元测试

测试覆盖：
1. 空文本处理
2. DashScope API 调用
3. Gemini API 调用
4. 未知 Provider 降级
"""
from unittest.mock import Mock, patch

import pytest
from src.lucidpanda.services.embedding_service import (
    EmbeddingService,
    embedding_service,
)


class TestEmbeddingService:
    """EmbeddingService 测试类"""

    def test_encode_empty_text(self):
        """测试空文本处理"""
        result = embedding_service.encode("")
        assert result == []

        result = embedding_service.encode(None)
        assert result == []

    @patch('src.lucidpanda.services.embedding_service.dashscope')
    @patch('src.lucidpanda.services.embedding_service.TextEmbedding')
    def test_encode_dashscope_success(self, mock_text_embedding, mock_dashscope):
        """测试 DashScope 成功编码"""
        # Mock 配置
        with patch('src.lucidpanda.services.embedding_service.settings') as mock_settings:
            mock_settings.EMBEDDING_PROVIDER = 'dashscope'
            mock_settings.DASHSCOPE_API_KEY = 'test_key'
            mock_settings.DASHSCOPE_EMBEDDING_MODEL = 'text-embedding-v3'
            mock_settings.DASHSCOPE_EMBEDDING_DIMENSIONS = 768

            # Mock API 响应
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.output = {
                'embeddings': [{
                    'embedding': [0.1] * 768
                }]
            }
            mock_text_embedding.call.return_value = mock_response

            # 测试
            result = EmbeddingService._encode_dashscope("测试文本")

            assert len(result) == 768
            assert result[0] == 0.1
            mock_text_embedding.call.assert_called_once()

    @patch('src.lucidpanda.services.embedding_service.genai')
    def test_encode_gemini_success(self, mock_genai):
        """测试 Gemini 成功编码"""
        # Mock 配置
        with patch('src.lucidpanda.services.embedding_service.settings') as mock_settings:
            mock_settings.EMBEDDING_PROVIDER = 'gemini'
            mock_settings.GEMINI_API_KEY = 'test_key'
            mock_settings.GEMINI_EMBEDDING_MODEL = 'models/gemini-embedding-001'

            # Mock API 响应
            mock_client = Mock()
            mock_genai.Client.return_value = mock_client

            mock_embedding = Mock()
            mock_embedding.values = [0.2] * 768

            mock_response = Mock()
            mock_response.embeddings = [mock_embedding]
            mock_client.models.embed_content.return_value = mock_response

            # 测试
            result = EmbeddingService._encode_gemini("测试文本")

            assert len(result) == 768
            assert result[0] == 0.2

    @patch('src.lucidpanda.services.embedding_service.EmbeddingService._encode_dashscope')
    def test_encode_auto_fallback(self, mock_encode_dashscope):
        """测试自动降级到 DashScope"""
        mock_encode_dashscope.return_value = [0.3] * 768

        with patch('src.lucidpanda.services.embedding_service.settings') as mock_settings:
            mock_settings.EMBEDDING_PROVIDER = 'unknown_provider'

            result = embedding_service.encode("测试")

            assert len(result) == 768
            mock_encode_dashscope.assert_called_once()

    @patch('src.lucidpanda.services.embedding_service.logger')
    def test_encode_logs_warning_for_unknown_provider(self, mock_logger):
        """测试未知 Provider 记录警告日志"""
        with patch('src.lucidpanda.services.embedding_service.settings') as mock_settings:
            mock_settings.EMBEDDING_PROVIDER = 'unknown'

            with patch.object(EmbeddingService, '_encode_dashscope') as mock_encode:
                mock_encode.return_value = [0.1] * 768
                embedding_service.encode("测试")

                mock_logger.warning.assert_called_once()


class TestEmbeddingServiceRetry:
    """重试机制测试"""

    @patch('src.lucidpanda.services.embedding_service.time.sleep')
    @patch('src.lucidpanda.services.embedding_service.dashscope')
    @patch('src.lucidpanda.services.embedding_service.TextEmbedding')
    def test_dashscope_retry_on_failure(self, mock_text_embedding, mock_dashscope, mock_sleep):
        """测试 DashScope 失败重试"""
        # Mock 配置
        with patch('src.lucidpanda.services.embedding_service.settings') as mock_settings:
            mock_settings.DASHSCOPE_API_KEY = 'test_key'
            mock_settings.DASHSCOPE_EMBEDDING_MODEL = 'text-embedding-v3'
            mock_settings.DASHSCOPE_EMBEDDING_DIMENSIONS = 768

            # Mock API 响应：前两次失败，第三次成功
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.output = {'embeddings': [{'embedding': [0.1] * 768}]}

            mock_response_failure = Mock()
            mock_response_failure.status_code = 500
            mock_response_failure.code = '500'
            mock_response_failure.message = 'Internal Error'

            mock_text_embedding.call.side_effect = [
                Exception("API Error 1"),
                Exception("API Error 2"),
                mock_response_success
            ]

            # 测试
            result = EmbeddingService._encode_dashscope("测试")

            assert len(result) == 768
            assert mock_text_embedding.call.call_count == 3
            mock_sleep.assert_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
