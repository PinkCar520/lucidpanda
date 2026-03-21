"""
Embedding Service - 文本向量化服务

负责将文本转换为嵌入向量（Embedding Vector），用于：
- 新闻去重（语义相似度计算）
- 语义搜索
- 事件聚类

支持的提供商：
    1. dashscope: 阿里云通义千问（推荐，国内稳定）
    2. gemini: Google Gemini（需要代理）

注意：
    已禁用本地模型降级，避免内存占用（4 核 4G 服务器会卡顿）

示例：
    >>> from src.lucidpanda.services.embedding_service import embedding_service
    >>> vector = embedding_service.encode("测试文本")
    >>> len(vector)
    768
"""
import logging
import time
from http import HTTPStatus
from typing import List

from src.lucidpanda.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Embedding 服务类
    
    提供文本向量化功能，支持多种云服务商 API。
    
    Attributes:
        None (类方法，无状态)
        
    Raises:
        Exception: 当所有 API 提供商都失败时抛出异常
        
    Example:
        >>> vector = EmbeddingService.encode("你好世界")
        >>> assert len(vector) == 768
    """

    @classmethod
    def _encode_gemini(cls, text: str) -> List[float]:
        """
        使用 Gemini Cloud API 生成向量
        
        Args:
            text: 输入文本
            
        Returns:
            768 维向量（List[float]）
            
        Raises:
            Exception: API 调用失败时抛出异常
            
        Note:
            - 维度固定为 768
            - 需要配置 HTTP_PROXY/HTTPS_PROXY
            - 有每日配额限制（10K RPD）
        """
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)

                res = client.models.embed_content(
                    model=settings.GEMINI_EMBEDDING_MODEL,
                    contents=text,
                    config={"output_dimensionality": 768}
                )
                return res.embeddings[0].values
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"⚠️ Gemini Embedding API 第 {attempt+1} 次尝试失败：{e}. 正在重试..."
                    )
                    time.sleep(1)
                else:
                    logger.error(f"❌ Gemini Embedding API 彻底失败：{e}")
                    raise e

    @classmethod
    def _encode_dashscope(cls, text: str) -> List[float]:
        """
        使用阿里云 DashScope Embedding API 生成向量
        
        Args:
            text: 输入文本
            
        Returns:
            可配置维度的向量（默认 768 维）
            
        Raises:
            Exception: API 调用失败时抛出异常
            
        Note:
            - 支持弹性维度：1024/768/512/256/128/64
            - 国内访问稳定，无需代理
            - 免费额度：50 万 tokens
        """
        max_retries = 2
        
        for attempt in range(max_retries + 1):
            try:
                import dashscope
                from dashscope import TextEmbedding
                
                # 显式设置 API Key
                dashscope.api_key = settings.DASHSCOPE_API_KEY

                res = TextEmbedding.call(
                    model=settings.DASHSCOPE_EMBEDDING_MODEL,
                    input=text,
                    dimension=settings.DASHSCOPE_EMBEDDING_DIMENSIONS
                )

                if res.status_code == HTTPStatus.OK:
                    return res.output['embeddings'][0]['embedding']
                else:
                    raise Exception(f"DashScope API error: {res.code} - {res.message}")
                    
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(
                        f"⚠️ DashScope Embedding API 第 {attempt+1} 次尝试失败：{e}. 正在重试..."
                    )
                    time.sleep(1)
                else:
                    logger.error(f"❌ DashScope Embedding API 彻底失败：{e}")
                    raise e

    @classmethod
    def encode(cls, text: str) -> List[float]:
        """
        根据配置生成文本嵌入向量
        
        根据 `EMBEDDING_PROVIDER` 配置选择合适的提供商。
        不支持降级到本地模型（已禁用，避免内存占用）。
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量（List[float]），维度取决于提供商：
            - DashScope: 768 维（可配置）
            - Gemini: 768 维
            
        Raises:
            Exception: API 调用失败时抛出异常（不再降级到本地模型）
            
        Example:
            >>> vector = embedding_service.encode("测试文本")
            >>> assert len(vector) == 768
            >>> assert all(isinstance(x, float) for x in vector)
        """
        if not text:
            return []

        provider = settings.EMBEDDING_PROVIDER.lower()

        if provider == "dashscope":
            return cls._encode_dashscope(text)
        elif provider == "gemini":
            return cls._encode_gemini(text)
        else:
            # 未知 provider，默认使用 DashScope
            logger.warning(f"未知的 Embedding 提供商 '{provider}'，使用 DashScope")
            return cls._encode_dashscope(text)


# 单例实例
embedding_service = EmbeddingService()
