from pathlib import Path
from typing import Optional

from job_status import set_job_status


def execute_ingestion_pipeline(
    file_path: str,
    filename: str,
    job_id: str,
    user_id: str = "anonymous",
    task_id: Optional[str] = None,
) -> dict:
    try:
        set_job_status(job_id, "processing", 15, "Extracting text...", task_id=task_id)
        from ingestion.router import route_file

        blocks = route_file(file_path, "upload", "Unknown")

        set_job_status(job_id, "processing", 40, "Chunking text...", task_id=task_id)
        from chunking.chunker import process_blocks

        chunks = process_blocks(blocks)
        for chunk in chunks:
            chunk["user_id"] = user_id

        set_job_status(job_id, "processing", 65, "Classifying chunks...", task_id=task_id)
        from classification.rule_classifier import classify_chunks

        classified = classify_chunks(chunks)

        set_job_status(job_id, "processing", 85, "Embedding and indexing...", task_id=task_id)
        from embedding.embedder import embed_chunks
        from retrieval.bm25_store import build_bm25_index
        from vectorstore.chroma_store import upsert_chunks

        vectors = embed_chunks(classified)
        upsert_chunks(classified, vectors)
        build_bm25_index(classified, user_id)

        set_job_status(
            job_id,
            "completed",
            100,
            f"Successfully ingested {len(classified)} chunks from {filename}",
            task_id=task_id,
        )
        return {"job_id": job_id, "chunks": len(classified)}
    except Exception as exc:
        set_job_status(job_id, "error", 0, str(exc), task_id=task_id)
        raise
    finally:
        if file_path and not str(file_path).startswith(("http://", "https://")):
            path = Path(file_path)
            if path.exists():
                path.unlink()
