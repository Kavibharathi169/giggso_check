import hashlib
import logging
import json
import os
from datetime import datetime, timezone

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "./output")


def _generate_chunk_id(file_path: str, row_index: int) -> str:
    """Generate a unique chunk ID using SHA256 hash."""
    return hashlib.sha256(
        (file_path + str(row_index)).encode("utf-8")
    ).hexdigest()[:16]


def _save_blocks(blocks: list[dict]) -> None:
    """Append blocks to scraped.jsonl output file."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "scraped.jsonl")
    try:
        with open(output_path, "a", encoding="utf-8") as f:
            for block in blocks:
                f.write(
                    json.dumps(block, ensure_ascii=False) + "\n"
                )
        logger.info(f"Saved {len(blocks)} blocks to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save blocks: {e}")


def load_csv(
    file_path    : str,
    document_type: str,
    org_name     : str
) -> list[dict]:
    """
    Load and extract text from a CSV file.
    Each row becomes one block.
    Returns list of block dicts.
    """
    logger.info(f"Loading CSV: {file_path}")

    if not os.path.exists(file_path):
        logger.error(f"CSV file not found: {file_path}")
        return []

    document_title = os.path.basename(file_path)
    section_title  = os.path.splitext(
        os.path.basename(file_path)
    )[0]
    extracted_at   = datetime.now(timezone.utc).isoformat()
    blocks         = []

    # Try common encodings
    df = None
    for encoding in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
        try:
            df = pd.read_csv(file_path, encoding=encoding)
            logger.info(
                f"Read CSV with encoding: {encoding}"
            )
            break
        except Exception:
            continue

    if df is None:
        logger.error(
            f"Failed to read CSV with any encoding: {file_path}"
        )
        return []

    if df.empty:
        logger.warning(f"CSV file is empty: {file_path}")
        return []

    # Clean column names
    df.columns = [str(col).strip() for col in df.columns]
    headers    = list(df.columns)

    logger.info(
        f"CSV loaded — rows: {len(df)}, "
        f"columns: {len(headers)}"
    )

    for row_index, row in df.iterrows():
        # Build text as "Column: value, Column: value"
        row_parts = []
        for header in headers:
            value = str(row[header]).strip()
            if value and value.lower() not in ["nan", "none", ""]:
                row_parts.append(f"{header}: {value}")

        if not row_parts:
            logger.debug(f"Skipping empty row {row_index}")
            continue

        text     = ", ".join(row_parts)
        chunk_id = _generate_chunk_id(file_path, row_index)

        block = {
            "chunk_id"      : chunk_id,
            "source_url"    : file_path,
            "document_title": document_title,
            "organization"  : org_name,
            "section_title" : section_title,
            "section_level" : "",
            "chapter"       : "",
            "article"       : "",
            "content_type"  : "paragraph",
            "text"          : text,
            "char_count"    : len(text),
            "extracted_at"  : extracted_at,
        }
        blocks.append(block)

    _save_blocks(blocks)

    logger.info(
        f"CSV loading complete. "
        f"Rows extracted: {len(blocks)} from {file_path}"
    )
    return blocks