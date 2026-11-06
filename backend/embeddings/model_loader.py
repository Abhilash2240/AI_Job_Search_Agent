# backend/embeddings/model_loader.py
import os
from functools import lru_cache
from sentence_transformers import SentenceTransformer

# Path to the fine‑tuned model directory (relative to project root)
MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "models", "trained_sbert")

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load the fine‑tuned SBERT model once and cache it.
    Returns
    -------
    SentenceTransformer
        The loaded model instance.
    """
    model_path = os.path.abspath(MODEL_DIR)
    if not os.path.isdir(model_path):
        raise FileNotFoundError(f"SBERT model directory not found: {model_path}")
    # Enable torch‑cuda if available, otherwise fallback to CPU
    device = "cuda" if os.getenv("CUDA_VISIBLE_DEVICES") or os.getenv("TORCH_CUDA_ARCH_LIST") else "cpu"
    return SentenceTransformer(model_path, device=device)

