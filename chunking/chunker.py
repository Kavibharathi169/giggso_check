import hashlib
import logging
import json
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from chunking.token_utils import count_tokens, tiktoken_length
import re

load_dotenv()

logger = logging.getLogger(__name__)
OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")

# multilingual-e5-* uses max ~512 tokens; larger chunks are truncated in the embedder.
MAX_TOKENS = int(os.getenv("CHUNK_MAX_TOKENS", "512"))
OVERLAP = int(os.getenv("CHUNK_OVERLAP", "128"))
if OVERLAP >= MAX_TOKENS:
    OVERLAP = max(0, MAX_TOKENS // 8)
SEPARATORS = ["\n\n", "\n", ".", "!", "?", " ", ""]


def _get_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        chunk_size       = MAX_TOKENS,
        chunk_overlap    = OVERLAP,
        length_function  = tiktoken_length,
        separators       = SEPARATORS,
    )

def _cosine_sim(u, v) -> float:
    # SentenceTransformer vectors are normalized in our embedder, so dot ~= cosine.
    try:
        return float(u @ v)
    except Exception:
        # Fallback for list types
        s = 0.0
        for a, b in zip(u, v):
            s += float(a) * float(b)
        return s

def _split_into_units(text: str) -> list[str]:
    """
    Split into semantic-ish units without losing wording.
    We prefer paragraphs; if a paragraph is huge, keep it as-is and let token limits enforce boundaries.
    """
    if not text or not text.strip():
        return []
    parts = [p.strip() for p in text.split("\n\n") if p and p.strip()]
    return parts if parts else [text.strip()]

_HEADING_RE = re.compile(r"^\s*((?:\d+\.)+\d+|\d+)(?:\s*[:.)-]|\s+)(.{0,120})\s*$")

def _extract_section_heading(text: str) -> str:
    """
    Best-effort heading extraction.
    Looks at the first few non-empty lines for patterns like:
    - "3.1 Access Control"
    - "4.2: Logging"
    - "12) Incident Response"
    """
    if not text or not text.strip():
        return ""
    lines = [ln.strip() for ln in text.splitlines() if ln and ln.strip()]
    for ln in lines[:6]:
        m = _HEADING_RE.match(ln)
        if m:
            prefix = (m.group(1) or "").strip()
            title = (m.group(2) or "").strip()
            if title:
                return f"{prefix} {title}".strip()
            return prefix
    return ""

def _detect_is_table(text: str) -> int:
    if not text or not text.strip():
        return 0
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        return 0
    pipe_lines = sum(1 for ln in lines if ln.count("|") >= 2)
    tab_lines = sum(1 for ln in lines if "\t" in ln)
    # Heuristic: repeated column separators across several lines
    if pipe_lines >= 3 or tab_lines >= 3:
        return 1
    return 0

_ENTITY_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("GDPR", re.compile(r"\bGDPR\b", re.IGNORECASE)),
    ("DPA", re.compile(r"\bdata protection (act|authority)\b", re.IGNORECASE)),
    ("ISO 27001", re.compile(r"\bISO\s*27001\b", re.IGNORECASE)),
    ("SOC 2", re.compile(r"\bSOC\s*2\b", re.IGNORECASE)),
    ("SOX", re.compile(r"\bSOX\b|\bSarbanes[-\s]?Oxley\b", re.IGNORECASE)),
    ("NIST", re.compile(r"\bNIST\b", re.IGNORECASE)),
    ("PCI DSS", re.compile(r"\bPCI\s*DSS\b", re.IGNORECASE)),
    ("HIPAA", re.compile(r"\bHIPAA\b", re.IGNORECASE)),
    ("Article", re.compile(r"\bArticle\s+\d{1,3}\b", re.IGNORECASE)),
]

def _extract_entities(text: str) -> str:
    if not text or not text.strip():
        return ""
    found: list[str] = []
    for label, pat in _ENTITY_PATTERNS:
        if pat.search(text):
            found.append(label)
    # stable, deduped
    out = sorted(set(found))
    return ", ".join(out)

def _save_chunks(chunks: list[dict]) -> None:
    if os.getenv("SAVE_CHUNK_JSONL", "false").lower() not in ("1", "true", "yes"):
        return
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "chunked.jsonl")
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            for chunk in chunks:
                f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        logger.info(f"Saved {len(chunks)} chunks to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save chunks: {e}")

def _build_chunk(text: str, base_block: dict, chunk_index: int, source_format: str) -> dict:
    chunk = dict(base_block)
    base_id = base_block.get("chunk_id", "")
    unique_id = hashlib.sha256(f"{base_id}_{chunk_index}_{text[:32]}".encode("utf-8")).hexdigest()[:16]
    chunk["chunk_id"]      = unique_id
    chunk["text"]          = text
    chunk["char_count"]    = len(text)
    chunk["token_count"]   = count_tokens(text)
    chunk["chunk_index"]   = chunk_index
    chunk["source_format"] = source_format
    # Enrichment for retrieval + citations
    chunk["page_number"]   = base_block.get("page_number")
    chunk["section_heading"] = (
        base_block.get("section_heading")
        or _extract_section_heading(text)
        or base_block.get("section_title", "")
    )
    chunk["is_table"]      = _detect_is_table(text)
    chunk["named_entities"] = _extract_entities(text)
    return chunk

def _semantic_chunking(blocks: list[dict], source_format: str) -> list[dict]:
    """
    Semantic chunking using embeddings:
    - Split text into paragraph units
    - Embed units and create chunk boundaries when topical similarity drops
    - Enforce MAX_TOKENS budget and add an approximate overlap by reusing trailing units

    If embeddings can't be loaded, falls back to RecursiveCharacterTextSplitter behavior.
    """
    if not blocks:
        return []

    # Tunables (kept conservative for governance docs)
    sim_threshold = float(os.getenv("SEMANTIC_SIM_THRESHOLD", "0.70"))
    min_tokens = int(os.getenv("SEMANTIC_MIN_TOKENS", str(max(64, MAX_TOKENS // 4))))

    # Prepare units in document order while keeping a stable "base block" for metadata.
    units: list[tuple[str, dict, int]] = []  # (unit_text, base_block, token_count)
    for b in blocks:
        raw = (b.get("text") or "").strip()
        if not raw:
            continue
        for u in _split_into_units(raw):
            t = count_tokens(u)
            if t > 0:
                units.append((u, b, t))

    if not units:
        return []

    # Try embedding-based semantic boundaries; fallback to recursive splitting if anything fails.
    try:
        from embedding.embedder import get_model
        import numpy as np

        model = get_model()
        unit_texts = [u[0] for u in units]
        # normalize_embeddings makes dot product == cosine similarity
        vecs = model.encode(
            ["passage: " + t for t in unit_texts],
            batch_size=max(1, min(int(os.getenv("EMBEDDING_BATCH_SIZE", "192")), len(unit_texts))),
            show_progress_bar=False,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )

        all_chunks: list[dict] = []
        chunk_index = 0

        cur_units: list[str] = []
        cur_tokens = 0
        cur_base_block = units[0][1]
        prev_vec = None

        def flush_with_overlap(next_start_idx: int) -> list[int]:
            nonlocal cur_units, cur_tokens, cur_base_block, prev_vec, chunk_index
            text = "\n\n".join([t for t in cur_units if t and t.strip()]).strip()
            if text:
                all_chunks.append(_build_chunk(text, cur_base_block, chunk_index, source_format))
                chunk_index += 1

            # approximate overlap: carry trailing units summing to ~OVERLAP tokens
            if OVERLAP <= 0:
                cur_units = []
                cur_tokens = 0
                prev_vec = None
                return []

            carried_idxs: list[int] = []
            tok_sum = 0
            j = next_start_idx - 1
            while j >= 0 and tok_sum < OVERLAP:
                tok_sum += units[j][2]
                carried_idxs.append(j)
                j -= 1
            carried_idxs.reverse()
            cur_units = [units[k][0] for k in carried_idxs]
            cur_tokens = sum(units[k][2] for k in carried_idxs)
            cur_base_block = units[carried_idxs[0]][1] if carried_idxs else units[next_start_idx][1]
            prev_vec = vecs[carried_idxs[-1]] if carried_idxs else None
            return carried_idxs

        i = 0
        while i < len(units):
            unit_text, base_block, tok = units[i]
            v = vecs[i]

            # Hard limit: if a single unit is bigger than MAX_TOKENS, split it recursively.
            if tok > MAX_TOKENS:
                # Flush current chunk before handling the big unit.
                if cur_units:
                    flush_with_overlap(i)
                splitter = _get_splitter()
                for sub in splitter.split_text(unit_text):
                    if sub and sub.strip():
                        all_chunks.append(_build_chunk(sub.strip(), base_block, chunk_index, source_format))
                        chunk_index += 1
                i += 1
                continue

            # Decide whether to start a new chunk.
            would_exceed = (cur_tokens + tok) > MAX_TOKENS if cur_units else False
            sim_drop = False
            if prev_vec is not None:
                sim = _cosine_sim(prev_vec, v)
                sim_drop = sim < sim_threshold

            if cur_units and (would_exceed or (sim_drop and cur_tokens >= min_tokens)):
                flush_with_overlap(i)

            if not cur_units:
                cur_base_block = base_block

            cur_units.append(unit_text)
            cur_tokens += tok
            prev_vec = v
            i += 1

        # Final flush
        if cur_units:
            text = "\n\n".join([t for t in cur_units if t and t.strip()]).strip()
            if text:
                all_chunks.append(_build_chunk(text, cur_base_block, chunk_index, source_format))

        return all_chunks

    except Exception as e:
        logger.warning("Semantic chunking unavailable; falling back to RecursiveCharacterTextSplitter (%s)", e)
        splitter = _get_splitter()
        all_chunks: list[dict] = []
        chunk_index = 0
        buffer_text = ""
        buffer_block = blocks[0]

        for block in blocks:
            text = (block.get("text") or "").strip()
            if not text:
                continue
            combined = f"{buffer_text}\n\n{text}" if buffer_text else text
            if count_tokens(combined) > MAX_TOKENS:
                if buffer_text.strip():
                    for sub in splitter.split_text(buffer_text):
                        if sub.strip():
                            all_chunks.append(_build_chunk(sub, buffer_block, chunk_index, source_format))
                            chunk_index += 1
                buffer_text = text
                buffer_block = block
            else:
                buffer_text = combined

        if buffer_text.strip():
            for sub in splitter.split_text(buffer_text):
                if sub.strip():
                    all_chunks.append(_build_chunk(sub, buffer_block, chunk_index, source_format))
                    chunk_index += 1

        return all_chunks

def process_blocks(blocks: list[dict]) -> list[dict]:
    if not blocks:
        return []

    # Detect source format for metadata only
    first_url = blocks[0].get("source_url", "").lower()
    if first_url.startswith("http"):
        source_format = "web"
    elif first_url.endswith(".docx") or first_url.endswith(".doc"):
        source_format = "word"
    elif first_url.endswith(".xlsx") or first_url.endswith(".xls") or first_url.endswith(".csv"):
        source_format = "spreadsheet"
    elif first_url.endswith(".pdf"):
        source_format = "pdf"
    elif first_url.endswith(".png") or first_url.endswith(".jpg") or first_url.endswith(".jpeg"):
        source_format = "image"
    else:
        source_format = "txt"

    # Unified semantic chunking strategy for all documents
    chunks = _semantic_chunking(blocks, source_format)

    _save_chunks(chunks)
    return chunks