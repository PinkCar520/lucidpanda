import logging
import os
import sys

# Ensure the root directory is in sys.path
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.lucidpanda.config import settings  # noqa: E402
from src.lucidpanda.core.deduplication import NewsDeduplicator  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VERIFY")

def test_lazy_loading():
    print(f"Current EMBEDDING_PROVIDER: {settings.EMBEDDING_PROVIDER}")
    print(f"Current ENABLE_SEMANTIC_DEDUPE: {settings.ENABLE_SEMANTIC_DEDUPE}")

    # Check if sentence_transformers is in sys.modules
    is_loaded = 'sentence_transformers' in sys.modules
    print(f"SentenceTransformer loaded initially? {is_loaded}")

    # Initialize Deduplicator
    print("\n--- Initializing NewsDeduplicator ---")
    deduplicator = NewsDeduplicator()

    is_loaded = 'sentence_transformers' in sys.modules
    print(f"SentenceTransformer loaded after init? {is_loaded}")

    # Perform a deduplication check the triggers embedding
    print("\n--- Running is_duplicate ('Hello world') ---")
    try:
        deduplicator.is_duplicate("Hello world")
    except Exception as e:
        print(f"Expected API error or other: {e}")

    is_loaded = 'sentence_transformers' in sys.modules
    print(f"SentenceTransformer loaded after is_duplicate? {is_loaded}")

if __name__ == "__main__":
    test_lazy_loading()
