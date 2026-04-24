import os
import json
import logging
import pickle
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# In-memory caches to avoid reloading index per user
_bm25_cache = {}
_corpus_cache = {}

def tokenize(text: str) -> list[str]:
    return text.lower().split()

def get_user_paths(user_id: str):
    user_dir = os.path.join(OUTPUT_DIR, user_id)
    os.makedirs(user_dir, exist_ok=True)
    return (
        os.path.join(user_dir, "bm25_index.pkl"),
        os.path.join(user_dir, "corpus.json")
    )

def build_bm25_index(chunks: list[dict], user_id: str = "anonymous"):
    """Builds and saves the BM25 index for a specific user from a list of chunk dicts."""
    global _bm25_cache, _corpus_cache

    bm25_path, corpus_path = get_user_paths(user_id)
    
    # Reload existing user corpus if any
    user_corpus = []
    if os.path.exists(corpus_path):
        try:
            with open(corpus_path, "r", encoding="utf-8") as f:
                user_corpus = json.load(f)
        except Exception:
            user_corpus = []

    # Append new chunks
    new_corpus = [{"id": c["chunk_id"], "text": c["text"], "metadata": c} for c in chunks]
    user_corpus.extend(new_corpus)

    # Save corpus
    with open(corpus_path, "w", encoding="utf-8") as f:
        json.dump(user_corpus, f, ensure_ascii=False)

    # Rebuild index for user
    if not user_corpus:
        logger.warning(f"BM25 corpus for {user_id} is empty, skipping index build.")
        _bm25_cache[user_id] = None
        _corpus_cache[user_id] = []
        return

    tokenized_corpus = [tokenize(doc["text"]) for doc in user_corpus]
    user_bm25 = BM25Okapi(tokenized_corpus)

    # Save index
    with open(bm25_path, "wb") as f:
        pickle.dump(user_bm25, f)

    _bm25_cache[user_id] = user_bm25
    _corpus_cache[user_id] = user_corpus

    logger.info(f"BM25 index built for user {user_id} with {len(user_corpus)} total documents.")

def load_bm25(user_id: str = "anonymous"):
    """Loads the BM25 index and corpus into memory for a specific user."""
    global _bm25_cache, _corpus_cache
    
    if user_id in _bm25_cache and user_id in _corpus_cache:
        return

    bm25_path, corpus_path = get_user_paths(user_id)

    if os.path.exists(bm25_path) and os.path.exists(corpus_path):
        try:
            with open(corpus_path, "r", encoding="utf-8") as f:
                _corpus_cache[user_id] = json.load(f)
            with open(bm25_path, "rb") as f:
                _bm25_cache[user_id] = pickle.load(f)
            logger.info(f"Loaded external BM25 index for user {user_id}.")
        except Exception as e:
            logger.error(f"Failed to load BM25 index for user {user_id}: {e}")
            _bm25_cache[user_id] = None
            _corpus_cache[user_id] = []
    else:
        _bm25_cache[user_id] = None
        _corpus_cache[user_id] = []

def search_bm25(query: str, top_k: int = 5, user_id: str = "anonymous") -> list[dict]:
    """Search the BM25 index for a specific user and return the top_k results."""
    load_bm25(user_id)
    
    user_bm25 = _bm25_cache.get(user_id)
    user_corpus = _corpus_cache.get(user_id)
    
    if not user_bm25 or not user_corpus:
        return []

    tokenized_query = tokenize(query)
    doc_scores = user_bm25.get_scores(tokenized_query)

    # Get top-k indices
    top_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)[:top_k]

    results = []
    for idx in top_indices:
        if doc_scores[idx] > 0:  # Only add if there's actually a keyword match
            doc = user_corpus[idx]
            metadata = doc.get("metadata", {}) or {}
            results.append(
                {
                    "chunk_id": doc.get("id", ""),
                    "text": doc.get("text", ""),
                    "metadata": metadata,
                    "score": float(doc_scores[idx]),
                }
            )

    return results
