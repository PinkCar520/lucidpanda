# src/alphasignal/services/embedding_service.py
import logging
import numpy as np
from src.alphasignal.config import settings

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    负责生成文本嵌入向量。
    支持两种模式：
    1. local: 使用本地 SentenceTransformer 模型 (1.7GB RAM)
    2. gemini: 使用 Google Gemini Embedding API (低内存)
    """
    _local_model = None

    @classmethod
    def _get_local_model(cls):
        if cls._local_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                model_name = settings.DEDUPE_MODEL_NAME
                logger.info(f"Loading local SentenceTransformer model: {model_name}...")
                cls._local_model = SentenceTransformer(model_name)
                logger.info("Local model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load local SentenceTransformer: {e}")
                raise e
        return cls._local_model

    @classmethod
    def _encode_local(cls, text: str) -> list[float]:
        model = cls._get_local_model()
        vector = model.encode(text)
        return vector.tolist()

    @classmethod
    def _encode_gemini(cls, text: str) -> list[float]:
        """使用 Gemini Cloud API 生成向量 (Dimension: 768 for text-embedding-004)"""
        try:
            from google import genai
            client = genai.Client(api_key=settings.GEMINI_API_KEY)
            
            # 备注：Gemini Embedding API 调用
            # 参考: client.models.embed_content(model=..., contents=...)
            res = client.models.embed_content(
                model=settings.GEMINI_EMBEDDING_MODEL,
                contents=text,
                config={
                    "output_dimensionality": 768
                }
            )
            return res.embeddings[0].values
        except Exception as e:
            logger.error(f"Gemini Embedding API failed: {e}")
            raise e

    @classmethod
    def encode(cls, text: str) -> list[float]:
        """根据配置生成向量并在必要时返回 list。"""
        if not text:
            return []
            
        provider = settings.EMBEDDING_PROVIDER.lower()
        
        if provider == "gemini":
            return cls._encode_gemini(text)
        elif provider == "openai":
            # TODO: 实现 OpenAI Embedding
            logger.warning("OpenAI embedding not implemented, falling back to local.")
            return cls._encode_local(text)
        else:
            return cls._encode_local(text)

embedding_service = EmbeddingService()
