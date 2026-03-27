"""
LLMFactory 单元测试

测试覆盖：
1. LLM 实例创建
2. 降级顺序配置化
3. 未知 Provider 处理
"""
import pytest
from unittest.mock import patch, Mock
from src.lucidpanda.core.engine import LLMFactory
from src.lucidpanda.config.llm_config import LLMConfigManager


class TestLLMFactory:
    """LLMFactory 测试类"""

    def test_create_qwen_llm(self):
        """测试创建 Qwen LLM 实例"""
        with patch('src.lucidpanda.core.engine.QwenLLM') as mock_qwen:
            llm = LLMFactory.create('qwen')
            mock_qwen.assert_called_once()

    def test_create_deepseek_llm(self):
        """测试创建 DeepSeek LLM 实例"""
        with patch('src.lucidpanda.core.engine.DeepSeekLLM') as mock_deepseek:
            llm = LLMFactory.create('deepseek')
            mock_deepseek.assert_called_once()

    def test_create_gemini_llm(self):
        """测试创建 Gemini LLM 实例"""
        with patch('src.lucidpanda.core.engine.GeminiLLM') as mock_gemini:
            llm = LLMFactory.create('gemini')
            mock_gemini.assert_called_once()

    def test_create_unknown_llm(self):
        """测试创建未知 LLM 实例"""
        with pytest.raises(ValueError, match="未知的 LLM 提供商"):
            LLMFactory.create('unknown_provider')

    def test_create_llm_case_insensitive(self):
        """测试 LLM 创建不区分大小写"""
        with patch('src.lucidpanda.core.engine.QwenLLM') as mock_qwen:
            LLMFactory.create('QWEN')
            mock_qwen.assert_called_once()
            
        with patch('src.lucidpanda.core.engine.QwenLLM') as mock_qwen:
            LLMFactory.create('Qwen')
            mock_qwen.assert_called_once()


class TestLLMFactoryFallback:
    """LLMFactory 降级逻辑测试"""

    @patch('src.lucidpanda.core.engine.settings')
    @patch('src.lucidpanda.core.engine.LLMConfigManager')
    def test_get_fallback_from_config(self, mock_config_manager, mock_settings):
        """测试从配置读取降级顺序"""
        # 配置降级顺序
        mock_settings.LLM_FALLBACK_ORDER = ['qwen', 'deepseek', 'gemini']
        
        # Mock Qwen 可用
        mock_qwen_config = Mock()
        mock_qwen_config.enabled = True
        
        mock_config_manager.get_active_llm.return_value = mock_qwen_config
        
        # 测试：主力是 deepseek，应该返回 qwen 作为备用
        fallback = LLMFactory.get_fallback_provider('deepseek')
        
        assert fallback == 'qwen'

    @patch('src.lucidpanda.core.engine.settings')
    @patch('src.lucidpanda.core.engine.LLMConfigManager')
    def test_get_fallback_skip_unavailable(self, mock_config_manager, mock_settings):
        """测试跳过不可用的提供商"""
        # 配置降级顺序
        mock_settings.LLM_FALLBACK_ORDER = ['qwen', 'deepseek', 'gemini']
        
        # Mock Qwen 不可用，DeepSeek 可用
        mock_qwen_config = Mock()
        mock_qwen_config.enabled = False
        
        mock_deepseek_config = Mock()
        mock_deepseek_config.enabled = True
        
        mock_config_manager.get_active_llm.side_effect = lambda name: {
            'qwen': mock_qwen_config,
            'deepseek': mock_deepseek_config,
            'gemini': Mock(enabled=False)
        }[name]
        
        # 测试：跳过 Qwen，返回 DeepSeek
        fallback = LLMFactory.get_fallback_provider('gemini')
        
        assert fallback == 'deepseek'

    @patch('src.lucidpanda.core.engine.settings')
    def test_get_fallback_default(self, mock_settings):
        """测试默认降级逻辑"""
        # 配置降级顺序
        mock_settings.LLM_FALLBACK_ORDER = ['qwen', 'deepseek', 'gemini']
        
        # 测试：如果所有都不可用，返回第一个
        with patch('src.lucidpanda.core.engine.LLMConfigManager.get_active_llm') as mock_get:
            mock_get.return_value = Mock(enabled=False)
            
            fallback = LLMFactory.get_fallback_provider('unknown')
            
            # 应该返回第一个（qwen）
            assert fallback == 'qwen'

    @patch('src.lucidpanda.core.engine.settings')
    def test_get_fallback_custom_order(self, mock_settings):
        """测试自定义降级顺序"""
        # 配置自定义降级顺序
        mock_settings.LLM_FALLBACK_ORDER = ['deepseek', 'qwen']
        
        # Mock DeepSeek 可用
        mock_deepseek_config = Mock()
        mock_deepseek_config.enabled = True
        
        with patch('src.lucidpanda.core.engine.LLMConfigManager.get_active_llm') as mock_get:
            mock_get.return_value = mock_deepseek_config
            
            # 测试：主力是 qwen，应该返回 deepseek
            fallback = LLMFactory.get_fallback_provider('qwen')
            
            assert fallback == 'deepseek'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
