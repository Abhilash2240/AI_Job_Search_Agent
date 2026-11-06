# backend/embeddings/embedding_service.py
"""Utility for generating embeddings using the fine‑tuned SBERT model.
The service caches embeddings per input text to avoid recomputation.
"""
import hashlib
from functools import lru_cache
from typing import List
import numpy as np

from embeddings.model_loader import get_model

# Simple in‑memory cache (process‑lifetime). Keys are SHA‑256 of the text.
_embedding_cache: dict[str, np.ndarray] = {}

def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def embed_text(text: str) -> np.ndarray:
    """Return a 1‑D NumPy array embedding for a single piece of text.
    If the text was previously embedded, the cached result is returned.
    """
    key = _hash_text(text)
    if key in _embedding_cache:
        return _embedding_cache[key]
    model = get_model()
    # SentenceTransformer returns a 2‑D array [[...]]
    vec = model.encode([text], normalize_embeddings=True)[0]
    arr = np.array(vec, dtype=np.float32)
    _embedding_cache[key] = arr
    return arr

def embed_batch(texts: List[str]) -> np.ndarray:
    """Encode a list of texts and return a 2‑D NumPy array (N, dim).
    Cache is used for any already‑seen texts.
    """
    if not texts:
        return np.empty((0, get_model().get_sentence_embedding_dimension()), dtype=np.float32)
    # Compute hashes and split already‑cached vs new
    new_texts = []
    new_indices = []
    results = []
    for i, txt in enumerate(texts):
        key = _hash_text(txt)
        if key in _embedding_cache:
            results.append(_embedding_cache[key])
        else:
            new_texts.append(txt)
            new_indices.append(i)
    if new_texts:
        model = get_model()
        new_vecs = model.encode(new_texts, normalize_embeddings=True)
        for idx, vec in zip(new_indices, new_vecs):
            arr = np.array(vec, dtype=np.float32)
            _embedding_cache[_hash_text(texts[idx])] = arr
            results.insert(idx, arr)
    return np.vstack(results)

