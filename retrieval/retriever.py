import logging
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Search Weight Tuning Variables
# ALPHA controls the balance between Vector (Semantic) and BM25 (Keyword) Search.
# ALPHA = 0.7 means 70% Vector and 30% Keyword importance.
# Higher Alpha = better for conceptual questions ("What are the duties?")
# Lower Alpha = better for exact matches ("Section 3.2.1", "ISO 27001")
ALPHA = float(os.getenv("SEARCH_WEIGHT_ALPHA", "0.7"))
RETRIEVAL_DEBUG_LOG = os.getenv("RETRIEVAL_DEBUG_LOG", "false").lower() in ("1", "true", "yes")

_reranker = None

def _get_reranker():
    global _reranker
    if _reranker is not None:
        return _reranker

    enabled = os.getenv("RERANK_ENABLE", "true").lower() in ("1", "true", "yes")
    if not enabled:
        _reranker = False
        return None

    model_name = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    try:
        from sentence_transformers import CrossEncoder
        logger.info(f"Loading cross-encoder reranker: {model_name}")
        _reranker = CrossEncoder(model_name)
        return _reranker
    except Exception as e:
        logger.warning(f"Failed to load reranker ({model_name}): {e}")
        _reranker = False
        return None


def normalize_scores(results: list[dict], score_key: str = "score", reverse: bool = False) -> list[dict]:
    """Min-Max normalization for scores to combine dense and sparse results."""
    if not results:
        return []
    
    scores = [r.get(score_key, 0) for r in results]
    min_score, max_score = min(scores), max(scores)
    
    for r in results:
        raw_score = r.get(score_key, 0)
        if max_score > min_score:
            r['normalized_score'] = (raw_score - min_score) / (max_score - min_score)
        else:
            r['normalized_score'] = 1.0 # If all scores are the same
            
        # Invert if it's a distance metric (like L2 in vector search)
        if reverse:
            r['normalized_score'] = 1.0 - r['normalized_score']
            
    return results


def summarize_sentence_hits(results: list[dict]) -> list[dict]:
    out: list[dict] = []
    for rank, r in enumerate(results or [], 1):
        meta = r.get("metadata", {}) or {}
        out.append(
            {
                "rank": rank,
                "chunk_id": r.get("chunk_id", ""),
                "parent_chunk_id": meta.get("parent_chunk_id", ""),
                "sentence_index": meta.get("sentence_index", -1),
                "score": float(r.get("score", r.get("hybrid_score", 0.0)) or 0.0),
                "hybrid_score": float(r.get("hybrid_score", 0.0) or 0.0),
                "source_type": meta.get("source_type", ""),
                "section_heading": meta.get("section_heading") or meta.get("section_title", ""),
                "source_url": meta.get("source_url", ""),
                "text_preview": str(r.get("text", "") or "")[:220],
            }
        )
    return out

def retrieve(
    query         : str,
    content_domain: str = None,
    document_type : str = None,
    source_format : str = None,
    top_k         : int = 5,
    user_id       : str = "anonymous"
) -> list[dict]:
    if not query or not query.strip():
        logger.warning("retrieve called with empty query")
        return []

    from embedding.embedder import embed_query
    from vectorstore.chroma_store import search
    from retrieval.bm25_store import search_bm25

    # Intercept generic checklist prompt and transform it to semantic keywords
    if "Strictly format as JSON" in query:
        search_query = "compliance requirement rule policy obligation procedure control standard"
    else:
        search_query = query

    # Step 1: Embed query
    logger.info(f"Embedding query: '{search_query[:60]}'")
    try:
        query_vector = embed_query(search_query)
    except Exception as e:
        logger.error(f"Query embedding failed: {e}")
        return []

    # Step 2: Build metadata filters
    filters = {}
    if content_domain and content_domain != "all":
        filters["content_domain"] = content_domain
    if document_type and document_type != "all":
        filters["document_type"] = document_type
    if source_format and source_format != "all":
        filters["source_format"] = source_format
    if user_id:
        filters["user_id"] = user_id

    # We fetch more chunks to ensure good overlap for hybrid scoring
    fetch_k = max(top_k * 3, int(os.getenv("RETRIEVAL_FETCH_MULTIPLIER", "3")) * top_k)

    # Step 3: Search ChromaDB (Vector/Dense)
    semantic_results = []
    try:
        semantic_results = search(query_vector=query_vector, filters=filters, top_k=fetch_k)
        semantic_results = normalize_scores(semantic_results, score_key="score", reverse=False)
    except Exception as e:
        logger.error(f"Vector search failed: {e}")

    # Step 4: Search BM25 (Keyword/Sparse)
    keyword_results = search_bm25(search_query, top_k=fetch_k, user_id=user_id)
    # BM25 returns score where higher is better
    keyword_results = normalize_scores(keyword_results, score_key="score", reverse=False)

    # Step 5: Advanced Hybrid Weighting (Alpha Blending)
    merged_map = {}
    
    # Map vector results
    for res in semantic_results:
        cid = res.get("chunk_id", res.get("metadata", {}).get("chunk_id", ""))
        merged_map[cid] = {
            "doc": res,
            "vector_score": res.get("normalized_score", 0.0),
            "bm25_score": 0.0
        }
        
    # Map BM25 results
    for res in keyword_results:
        cid = res.get("chunk_id", res.get("metadata", {}).get("chunk_id", ""))
        if cid in merged_map:
            merged_map[cid]["bm25_score"] = res.get("normalized_score", 0.0)
        else:
            merged_map[cid] = {
                "doc": res,
                "vector_score": 0.0,
                "bm25_score": res.get("normalized_score", 0.0)
            }

    # Calculate final hybrid score
    unique_results = []
    for cid, data in merged_map.items():
        doc = data["doc"]
        # Hybrid formula
        doc["hybrid_score"] = (ALPHA * data["vector_score"]) + ((1.0 - ALPHA) * data["bm25_score"])
        unique_results.append(doc)

    # Sort down to combined top_k pool
    unique_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
    if not unique_results:
        return []

    # Take the best candidates for Re-Ranking
    candidate_mult = int(os.getenv("RERANK_CANDIDATE_MULTIPLIER", "2"))
    candidates = unique_results[: max(top_k, top_k * candidate_mult)]

    # Step 6: Cross-Encoder Re-Ranking (Now optimally cached and scaled)
    reranker = _get_reranker()
    if reranker:
        try:
            pairs = [[search_query, doc.get("text", "")] for doc in candidates]        
            scores = reranker.predict(pairs)

            for doc, score in zip(candidates, scores):
                doc["score"] = float(score)

            candidates.sort(key=lambda x: x["score"], reverse=True)
            results = candidates[:top_k]
        except Exception as e:
            logger.warning(f"Re-ranking failed, falling back to hybrid weights: {e}")
            results = candidates[:top_k]
    else:
        results = candidates[:top_k]

    # Clean up sorting keys
    for r in results:
        r.pop("normalized_score", None)
        r.pop("distance", None)

    if RETRIEVAL_DEBUG_LOG:
        for hit in summarize_sentence_hits(results):
            logger.info(
                "retrieval_hit rank=%s chunk_id=%s parent_chunk_id=%s sentence_index=%s score=%.4f source_type=%s",
                hit["rank"],
                hit["chunk_id"],
                hit["parent_chunk_id"],
                hit["sentence_index"],
                hit["score"],
                hit["source_type"],
            )

    logger.info(f"Retrieved {len(results)} results using ALPHA={ALPHA}")  
    return results


def build_context_string(results: list[dict]) -> str:
    if not results:
        return ""

    context_parts = []
    for i, r in enumerate(results, 1):
        meta    = r.get("metadata", {})
        text    = r.get("text", "")
        # score could be hybrid_score or cross-encoder score
        score   = r.get("score", r.get("hybrid_score", 0))
        section = meta.get("section_heading") or meta.get("section_title", "â€”")
        source  = meta.get("source_url", "â€”")
        domain  = meta.get("content_domain", "â€”")
        framework = meta.get("compliance_framework", "unspecified_framework")
        src_type = meta.get("source_type", "operational_guideline")
        page    = meta.get("page_number", 0)
        is_table = meta.get("is_table", 0)
        ents    = meta.get("named_entities", "")
        cid     = r.get("chunk_id") or meta.get("chunk_id", "")

        context_parts.append(
            f"[Chunk {i}]\n"
            f"chunk_id: {cid}\n"
            f"Section : {section}\n"
            f"Page    : {page}\n"
            f"Source  : {source}\n"
            f"Domain  : {domain}\n"
            f"Framework: {framework}\n"
            f"SourceType: {src_type}\n"
            f"Table   : {is_table}\n"
            f"Entities: {ents}\n"
            f"Score   : {score:.4f}\n"
            f"Text    : {text}\n"
        )

    return "\n".join(context_parts)


def retrieve_and_format(
    query         : str,
    content_domain: str = None,
    document_type : str = None,
    top_k         : int = 5,
    user_id       : str = "anonymous"
) -> tuple[list[dict], str]:
    results = retrieve(
        query          = query,
        content_domain = content_domain,
        document_type  = document_type,
        top_k          = top_k,
        user_id        = user_id
    )
    context = build_context_string(results)
    return results, context
