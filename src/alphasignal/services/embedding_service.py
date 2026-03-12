# src/alphasignal/services/embedding_service.py
import logging
from sentence_transformers import SentenceTransformer
import numpy as np

logger = logging.getLogger(__name__)

class EmbeddingService:
    """
    负责生成文本嵌入向量。
    复用 NewsDeduplicator 使用的 paraphrase-multilingual-MiniLM-L12-v2 模型。
    384 维度。
    """
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            try:
                model_name = "paraphrase-multilingual-MiniLM-L12-v2"
                logger.info(f"Loading SentenceTransformer model: {model_name}...")
                cls._model = SentenceTransformer(model_name)
                logger.info("Model loaded successfully.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer: {e}")
                # 降级处理或重试逻辑
                raise e
        return cls._model

    @classmethod
    def encode(cls, text: str) -> list[float]:
        """生成向量并转换为 list 以便 pgvector 使用。"""
        if not text:
            return []
        model = cls.get_model()
        vector = model.encode(text)
        return vector.tolist()

embedding_service = EmbeddingService()
