import re
import logging
from simhash import Simhash
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

# 历史层滑动窗口大小：保留最近 500 条，防止内存无限增长
# 500 条 ≈ 约 3劤7 天的情报量，足够拦截近期重复
MAX_HISTORY = 500

class NewsDeduplicator:
    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2", simhash_threshold=6, semantic_threshold=0.85, db=None):
        self.simhash_threshold = simhash_threshold
        self.semantic_threshold = semantic_threshold
        self.model_name = model_name
        self._model = None
        self.db = db  # IntelligenceDB 实例，用于 pgvector 语义查询
        
        # SimHash 历史（仍在内存维护，轻量级粗筛）
        self.simhash_history = []
        # 内存向量历史（仅当 db=None 时用作降级方案）
        self.vec_history = []
        self.id_history = []
        self.last_vector = None  # 最近一次编码结果，供外部持久化使用

    @property
    def model(self):
        if self._model is None:
            try:
                logger.info(f"Loading SentenceTransformer model: {self.model_name}...")
                self._model = SentenceTransformer(self.model_name)
                logger.info("Model loaded.")
            except Exception as e:
                logger.error(f"Failed to load SentenceTransformer model: {e}. Semantic deduplication will be disabled.")
                self._model = False # Mark as failed
        return self._model

    def normalize(self, text):
        """
        Text cleaning (denoising) standard.
        """
        if not text:
            return ""
            
        # Strip HTML tags
        text = re.sub(r'<[^>]+>', '', text)
            
        # Remove date patterns like (2024/01/01 ...)
        text = re.sub(r"\d{4}/\d{2}/\d{2}.*?\)", "", text)
        
        # Remove full-width/half-width parentheses
        text = re.sub(r"[（）()]", "", text)

        # Remove specific noise phrases
        noise = [
            "此为", "影响", "不确定性", "对市场",
            "微乎其微", "对经济影响", "但对市场影响有限"
        ]
        for n in noise:
            text = text.replace(n, "")
            
        return text.strip()

    def rough_duplicate(self, text_simhash):
        """
        SimHash rough filtering.
        Returns True if duplicate found in history.
        """
        for old_hash in self.simhash_history:
            if text_simhash.distance(old_hash) <= self.simhash_threshold:
                return True
        return False

    def semantic_duplicate(self, text_vector):
        """
        BERT semantic vector reranking.
        Returns True if duplicate found in history.
        """
        # cosine_similarity expects 2D arrays (n_samples, n_features)
        # text_vector is (n_features, ) or (1, n_features)
        
        if not self.vec_history:
            return False
            
        # Stack history for efficient batch calculation (optional, but loop is fine for now)
        # To avoid large matrix ops in a growing loop, iterating is acceptable for small batch sizes
        # or checking against the last N vectors. 
        # User spec: "for v in vectors".
        
        # Ensure text_vector is 2D
        vec = text_vector.reshape(1, -1)
        
        for v in self.vec_history:
            v_2d = v.reshape(1, -1)
            score = cosine_similarity(vec, v_2d)[0][0]
            if score > self.semantic_threshold:
                return True
        return False

    def is_duplicate(self, news_content, record_id=None):
        """
        综合判断函数。
        不是重复时更新历史。
        """
        clean_text = self.normalize(news_content)
        
        if not clean_text:
            return False

        # 1. SimHash 粗筛（内存，毫秒级）
        current_simhash = Simhash(clean_text)
        if self.rough_duplicate(current_simhash):
            return True

        # 2. 语义向量精筛
        current_vector = None
        if self.model:
            try:
                current_vector = self.model.encode(clean_text)
                self.last_vector = current_vector

                if self.db is not None:
                    # ★ pgvector 路径：查询 DB，O(log n)，持久化历史
                    if self.db.is_semantic_duplicate(current_vector, self.semantic_threshold):
                        return True
                else:
                    # 降级路径：内存遍历，仅用于单元测试
                    if self.semantic_duplicate(current_vector):
                        return True

            except Exception as e:
                logger.warning(f"Semantic encoding failed: {e}")
        else:
            self.last_vector = None

        # 3. 不是重复 → 加入 SimHash 历史
        self.add_to_history(current_simhash, current_vector if self.db is None else None, record_id)
            
        return False

    def add_to_history(self, sh_obj, vector, record_id=None):
        """Add an item to history, maintaining a FIFO sliding window."""
        self.simhash_history.append(sh_obj)
        self.vec_history.append(vector)
        if record_id:
            self.id_history.append(record_id)
        # FIFO 滑动窗口：超出上限则丢弃最旧的条目
        if len(self.simhash_history) > MAX_HISTORY:
            self.simhash_history = self.simhash_history[-MAX_HISTORY:]
            self.vec_history     = self.vec_history[-MAX_HISTORY:]
            self.id_history      = self.id_history[-MAX_HISTORY:]

    def clear_history(self):
        self.simhash_history = []
        self.vec_history = []
        self.id_history = []
