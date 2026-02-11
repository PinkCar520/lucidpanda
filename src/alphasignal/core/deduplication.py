import re
import logging
from simhash import Simhash
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger(__name__)

class NewsDeduplicator:
    def __init__(self, model_name="paraphrase-multilingual-MiniLM-L12-v2", simhash_threshold=6, semantic_threshold=0.85):
        self.simhash_threshold = simhash_threshold
        self.semantic_threshold = semantic_threshold
        self.model_name = model_name
        self._model = None
        
        # History containers for batch processing
        self.simhash_history = [] # List of Simhash objects
        self.vec_history = []     # List of numpy arrays (vectors)
        self.id_history = []      # List of IDs corresponding to the history
        self.last_vector = None   # Store the last calculated vector for caching

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
        Comprehensive judgement function.
        Updates history if NOT duplicate.
        """
        clean_text = self.normalize(news_content)
        
        if not clean_text:
            return False

        # 1. SimHash Rough Filter
        current_simhash = Simhash(clean_text)
        if self.rough_duplicate(current_simhash):
            return True

        # 2. Semantic Vector Filter (Only if model loaded successfully)
        current_vector = None
        if self.model: # Check if model is available (not False/None)
            try:
                current_vector = self.model.encode(clean_text)
                self.last_vector = current_vector # Store for external persistence
                if self.semantic_duplicate(current_vector):
                    return True
            except Exception as e:
                logger.warning(f"Semantic encoding failed: {e}")
        else:
            self.last_vector = None

        # 3. Not duplicate -> Add to history
        self.add_to_history(current_simhash, current_vector, record_id)
            
        return False

    def add_to_history(self, sh_obj, vector, record_id=None):
        """Manually add an item to history"""
        self.simhash_history.append(sh_obj)
        self.vec_history.append(vector)
        if record_id:
            self.id_history.append(record_id)

    def clear_history(self):
        self.simhash_history = []
        self.vec_history = []
        self.id_history = []
