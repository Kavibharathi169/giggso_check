import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PERSIST_DIR  = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
COLLECTION   = "governance_chunks"

_collection = None


# ── Get collection ────────────────────────────────────────────
def get_collection():
    """
    Get or create ChromaDB persistent collection.
    Uses cosine similarity space. Cached — avoids new PersistentClient per upsert.
    """
    global _collection
    import chromadb

    if _collection is not None:
        return _collection

    try:
        client = chromadb.PersistentClient(path=PERSIST_DIR)
        _collection = client.get_or_create_collection(
            name     = COLLECTION,
            metadata = {"hnsw:space": "cosine"}
        )
        logger.info(
            f"ChromaDB collection ready: {COLLECTION} "
            f"({_collection.count()} records)"
        )
        return _collection
    except Exception as e:
        logger.error(f"Failed to get ChromaDB collection: {e}")
        raise


# ── Upsert chunks ─────────────────────────────────────────────
def upsert_chunks(
    chunks : list[dict],
    vectors: list[list[float]]
) -> None:
    """
    Upsert chunks and their vectors into ChromaDB.
    Uses chunk_id as the record ID for deduplication.
    All metadata values must be str, int, or float.
    """
    if not chunks or not vectors:
        logger.warning("upsert_chunks called with empty data")
        return

    if len(chunks) != len(vectors):
        raise ValueError(
            f"Chunks ({len(chunks)}) and vectors "
            f"({len(vectors)}) count mismatch"
        )

    collection = get_collection()

    ids        = []
    documents  = []
    metadatas  = []
    embeddings = []

    for chunk, vector in zip(chunks, vectors):
        chunk_id = chunk.get("chunk_id", "")
        if not chunk_id:
            logger.warning("Chunk missing chunk_id — skipping")
            continue

        ids.append(chunk_id)
        documents.append(chunk.get("text", ""))
        embeddings.append(vector)

        # ChromaDB metadata must be str/int/float only
        # Convert None and bool to safe types
        meta = {
            "user_id"             : str(chunk.get("user_id", "anonymous")),
            "source_url"          : str(chunk.get("source_url","")           or ""),
            "document_title"      : str(chunk.get("document_title","")       or ""),
            "organization"        : str(chunk.get("organization","")         or ""),
            "section_title"       : str(chunk.get("section_title","")        or ""),
            "section_heading"     : str(chunk.get("section_heading","")      or ""),
            "section_level"       : str(chunk.get("section_level","")        or ""),
            "chapter"             : str(chunk.get("chapter","")              or ""),
            "article"             : str(chunk.get("article","")              or ""),
            "content_type"        : str(chunk.get("content_type","")         or ""),
            "source_format"       : str(chunk.get("source_format","")        or ""),
            "document_type"       : str(chunk.get("document_type","")        or ""),
            "content_domain"      : str(chunk.get("content_domain","")       or "unclassified"),
            "compliance_framework": str(chunk.get("compliance_framework","") or "unspecified_framework"),
            "source_type"         : str(chunk.get("source_type","")          or "operational_guideline"),
            "page_number"         : int(chunk.get("page_number",0)           or 0),
            "is_table"            : int(chunk.get("is_table",0)              or 0),
            "named_entities"      : str(chunk.get("named_entities","")       or ""),
            "token_count"         : int(chunk.get("token_count",0)           or 0),
            "chunk_index"         : int(chunk.get("chunk_index",0)           or 0),
        }
        metadatas.append(meta)

    batch_size = max(50, min(500, int(os.getenv("CHROMA_UPSERT_BATCH", "250"))))
    total      = len(ids)

    for i in range(0, total, batch_size):
        batch_ids   = ids[i:i+batch_size]
        batch_docs  = documents[i:i+batch_size]
        batch_metas = metadatas[i:i+batch_size]
        batch_embs  = embeddings[i:i+batch_size]

        try:
            collection.upsert(
                ids        = batch_ids,
                embeddings = batch_embs,
                documents  = batch_docs,
                metadatas  = batch_metas
            )
            logger.info(
                f"Upserted batch {i//batch_size + 1}: "
                f"{len(batch_ids)} records"
            )
        except Exception as e:
            logger.error(
                f"Failed to upsert batch starting at {i}: {e}"
            )
            raise

    logger.info(
        f"Upsert complete. "
        f"Total records: {total}"
    )


# ── Search ────────────────────────────────────────────────────
def search(
    query_vector: list[float],
    filters     : dict = {},
    top_k       : int  = 5
) -> list[dict]:
    """
    Search ChromaDB for most similar chunks.
    Applies optional metadata filters before search.
    Returns list of result dicts with text, metadata, score.
    """
    if not query_vector:
        logger.warning("search called with empty query vector")
        return []

    collection = get_collection()

    # Build query kwargs
    kwargs = {
        "query_embeddings" : [query_vector],
        "n_results"        : top_k,
        "include"          : ["documents", "metadatas",
                              "distances"]
    }

    # Apply metadata filters if provided
    if filters:
        # Remove None values from filters
        clean_filters = {
            k: v for k, v in filters.items()
            if v is not None and v != ""
        }
        if clean_filters:
            kwargs["where"] = clean_filters
            logger.info(f"Applying filters: {clean_filters}")

    try:
        results = collection.query(**kwargs)
    except Exception as e:
        logger.error(f"ChromaDB search failed: {e}")
        return []

    # Parse results
    output = []
    ids_list  = results.get("ids", [[]])[0]
    docs      = results.get("documents", [[]])[0]
    metas     = results.get("metadatas",  [[]])[0]
    distances = results.get("distances",  [[]])[0]

    for cid, doc, meta, dist in zip(ids_list, docs, metas, distances):
        output.append({
            "chunk_id": cid,
            "text"    : doc,
            "metadata": meta,
            "score"   : round(1 - dist, 4)
        })

    logger.info(
        f"Search returned {len(output)} results "
        f"(top score: "
        f"{output[0]['score'] if output else 'N/A'})"
    )
    return output


# ── Count records ─────────────────────────────────────────────
def count_records() -> int:
    """Return total number of records in the collection."""
    try:
        return get_collection().count()
    except Exception as e:
        logger.error(f"Failed to count records: {e}")
        return 0


# ── Delete collection ─────────────────────────────────────────
def clear_collection() -> None:
    """Delete and recreate the collection (wipes all data)."""
    import chromadb
    try:
        client = chromadb.PersistentClient(path=PERSIST_DIR)
        client.delete_collection(COLLECTION)
        logger.info(f"Collection {COLLECTION} cleared")
    except Exception as e:
        logger.warning(f"Could not clear collection: {e}")