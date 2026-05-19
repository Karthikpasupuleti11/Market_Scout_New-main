"""Text chunking and embeddings for RAG (lazy-loaded model)."""

import logging
import threading

logger = logging.getLogger(__name__)

_model = None
_model_lock = threading.Lock()


def _get_model():
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                logger.info("RAG — Loading embedding model all-MiniLM-L6-v2")
                _model = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("RAG — Embedding model loaded and ready")
    return _model


def preload():
    """Pre-warm the embedding model (call at startup to avoid first-request lag)."""
    _get_model()


def chunk_text(text, chunk_size=500, overlap=50):
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size]
        if chunk.strip():
            chunks.append({"text": chunk, "chunk_id": i})
    return chunks


def embed(texts):
    return _get_model().encode(texts)
