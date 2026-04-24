import logging
import os
from pathlib import Path
from dotenv import load_dotenv

# Load from project root .env
_root_env = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_root_env, override=True)

logger = logging.getLogger(__name__)

# ── Singleton model instance ──────────────────────────────────
_model = None


def _split_into_sentences(text: str) -> list[str]:
    import re
    if not text or not text.strip():
        return []
    compact = re.sub(r"\s+", " ", text).strip()
    # Keep this simple and robust across policy prose.
    parts = re.split(r"(?<=[.!?])\s+|(?<=:)\s+", compact)
    out = [p.strip() for p in parts if p and p.strip()]
    return out if out else [compact]


def get_model():
    """
    Load embedding model once and reuse.
    Uses intfloat/multilingual-e5-large-instruct by default.
    Runs fully locally — no API needed.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        model_name = os.getenv(
            "EMBEDDING_MODEL",
            "intfloat/multilingual-e5-large-instruct"
        )
        logger.info(f"Loading embedding model: {model_name}")
        try:
            _model = SentenceTransformer(model_name)
            try:
                import torch

                nt = int(os.getenv("TORCH_NUM_THREADS", "0"))
                if nt > 0:
                    torch.set_num_threads(nt)
            except Exception:
                pass
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    return _model


def embed_chunks(chunks: list[dict]) -> list[list[float]]:
    """
    Embed a list of chunk dicts into vectors.
    Uses 'passage: ' prefix as required by multilingual-e5.
    Returns list of float vectors.
    """
    if not chunks:
        logger.warning("embed_chunks called with empty list")
        return []

    model = get_model()

    # multilingual-e5 requires "passage: " prefix for documents
    texts = ["passage: " + c.get("text", "") for c in chunks]

    logger.info(f"Embedding {len(texts)} chunks in batches...")

    cap = int(os.getenv("EMBEDDING_BATCH_SIZE", "192"))
    dynamic_batch_size = max(1, min(cap, len(texts)))

    show_bar = os.getenv("EMBEDDING_SHOW_PROGRESS", "").lower() in ("1", "true", "yes")

    try:
        vectors = model.encode(
            texts,
            batch_size         = dynamic_batch_size,
            show_progress_bar  = show_bar,
            normalize_embeddings = True,
            convert_to_numpy   = True
        )
        logger.info(
            f"Embedding complete. "
            f"Shape: {vectors.shape}"
        )
        return vectors.tolist()
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise


def build_sentence_embedding_units(chunks: list[dict]) -> list[dict]:
    """
    Expand chunk documents into sentence-level embedding units.
    """
    units: list[dict] = []
    for chunk in chunks or []:
        text = str(chunk.get("text", "") or "").strip()
        if not text:
            continue
        chunk_id = str(chunk.get("chunk_id", "") or "")
        sentences = _split_into_sentences(text)
        if not sentences:
            sentences = [text]
        for idx, sentence in enumerate(sentences):
            unit = dict(chunk)
            unit["parent_chunk_id"] = chunk_id
            unit["sentence_index"] = idx
            unit["text"] = sentence
            unit["chunk_id"] = f"{chunk_id}::s{idx}" if chunk_id else f"sentence::{idx}"
            units.append(unit)
    return units


def embed_query(query: str) -> list[float]:
    """
    Embed a single user query into a vector.
    Uses 'query: ' prefix as required by multilingual-e5.
    Returns single float vector.
    """
    if not query or not query.strip():
        logger.warning("embed_query called with empty query")
        return []

    model = get_model()

    prefixed = "query: " + query.strip()

    try:
        vector = model.encode(
            [prefixed],
            normalize_embeddings = True,
            convert_to_numpy     = True
        )
        logger.info(
            f"Query embedded successfully: "
            f"'{query[:50]}'"
        )
        return vector[0].tolist()
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        raise