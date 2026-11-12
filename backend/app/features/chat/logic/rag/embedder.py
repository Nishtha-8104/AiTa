"""Local sentence embeddings for book RAG; the model loads on first use and stays resident."""

import logging
import threading

from app.features.chat.models import EMBED_DIM  # noqa: F401

logger = logging.getLogger(__name__)

MODEL_NAME = "BAAI/bge-small-en-v1.5"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
BATCH_SIZE = 32

_model = None
_lock = threading.Lock()


def _load_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(MODEL_NAME, device="cpu")


def _get_model():
    global _model
    if _model is None:
        with _lock:
            if _model is None:
                _model = _load_model()
    return _model


def embed(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    vectors = _get_model().encode(
        texts, batch_size=BATCH_SIZE, normalize_embeddings=True, show_progress_bar=False,
    )
    return vectors.tolist()


def embed_query(text: str) -> list[float]:
    return embed([QUERY_PREFIX + text])[0]


def warm_up() -> None:
    try:
        embed_query("warmup")
        logger.info("embedder %s loaded", MODEL_NAME)
    except Exception:
        logger.warning("embedder warm-up failed; it will load on first search", exc_info=True)


def warm_up_in_background() -> threading.Thread:
    thread = threading.Thread(target=warm_up, name="embedder-warmup", daemon=True)
    thread.start()
    return thread
