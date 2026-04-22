from fastapi import FastAPI, UploadFile, File, Form, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import os
import uuid
from typing import Optional
import gc

# Setup directories
os.makedirs("frontend", exist_ok=True)
os.makedirs("./output", exist_ok=True)

app = FastAPI(title="Governance AI API", version="2.0")

# CORS for frontend decoupling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import threading

def _prewarm_model():
    try:
        print("Pre-warming embedding model (background thread)...")
        from embedding.embedder import get_model
        get_model()
        print("Embedding model ready.")
    except Exception as e:
        print(f"Warning: Model pre-warm failed: {e}")

# Startup: Init db immediately; warm model in background so server starts fast
@app.on_event("startup")
async def startup_event():
    print("Initializing Database...")
    from storage.db import init_db
    init_db()
    # Warm model in background thread — server accepts requests immediately
    t = threading.Thread(target=_prewarm_model, daemon=True)
    t.start()
    print("Server ready. Model warming up in background...")

from celery_app import celery_app
from job_status import get_job_status, set_job_status
from queue_tasks import run_ingestion_pipeline
from ingestion_pipeline import execute_ingestion_pipeline

MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "50"))
UPLOAD_CHUNK_SIZE_BYTES = int(os.getenv("UPLOAD_CHUNK_SIZE_BYTES", str(1024 * 1024)))

class ChatRequest(BaseModel):
    query: str
    domain: Optional[str] = "all"
    user_id: Optional[str] = "anonymous"

def _run_ingestion_fallback(file_path: str, filename: str, job_id: str, user_id: str) -> None:
    fallback_task_id = f"local-{job_id}"
    execute_ingestion_pipeline(
        file_path=file_path,
        filename=filename,
        job_id=job_id,
        user_id=user_id,
        task_id=fallback_task_id,
    )
    gc.collect()


@app.post("/api/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None),
    link: Optional[str] = Form(None),
    user_id: str = Form("anonymous"),
):
    job_id = str(uuid.uuid4())
    os.makedirs(f"output/{user_id}", exist_ok=True)
    
    if link:
        # Process as a cloud link / webpage
        file_path = link
        filename = link
    elif file:
        # Process as a physical file upload
        file_path = os.path.join(f"output/{user_id}", f"{job_id}_{file.filename}")
        with open(file_path, "wb") as f:
            total_bytes = 0
            while True:
                chunk = await file.read(UPLOAD_CHUNK_SIZE_BYTES)
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > MAX_UPLOAD_MB * 1024 * 1024:
                    f.close()
                    try:
                        os.remove(file_path)
                    except OSError:
                        pass
                    raise HTTPException(
                        status_code=413,
                        detail=f"File exceeds max upload limit of {MAX_UPLOAD_MB} MB",
                    )
                f.write(chunk)
        filename = file.filename
    else:
        raise HTTPException(status_code=400, detail="Must provide either a file or a link")

    try:
        set_job_status(job_id, "queued", 0, "Job queued")
        task = run_ingestion_pipeline.delay(file_path, filename, job_id, user_id)
        set_job_status(job_id, "queued", 0, "Job queued", task_id=task.id)
        return {"job_id": job_id, "task_id": task.id, "message": "Upload successful, queued for background processing"}
    except Exception:
        # Fallback mode for local/dev environments where Redis/Celery is unavailable.
        fallback_task_id = f"local-{job_id}"
        set_job_status(
            job_id,
            "queued",
            0,
            "Queue unavailable, running local background processor",
            task_id=fallback_task_id,
        )
        background_tasks.add_task(_run_ingestion_fallback, file_path, filename, job_id, user_id)
        return {
            "job_id": job_id,
            "task_id": fallback_task_id,
            "message": "Upload successful, running local background processing",
            "mode": "local-fallback",
        }

@app.get("/api/status/{job_id}")
async def get_status(job_id: str):
    status = get_job_status(job_id)
    if status:
        return status

    # Best-effort fallback: if status record has expired but result backend still has task state
    raise HTTPException(status_code=404, detail="Job not found")


@app.get("/api/system/memory")
async def memory_settings():
    return {
        "max_upload_mb": MAX_UPLOAD_MB,
        "upload_chunk_size_bytes": UPLOAD_CHUNK_SIZE_BYTES,
        "local_status_ttl_sec": int(os.getenv("LOCAL_JOB_STATUS_TTL_SEC", "3600")),
        "local_status_max_items": int(os.getenv("LOCAL_JOB_STATUS_MAX_ITEMS", "2000")),
    }

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    from retrieval.retriever import retrieve_and_format
    from llm.generator import generate_answer, generate_checklist

    query_lower = request.query.lower()
    is_checklist = "checklist" in query_lower or "map " in query_lower
    
    # EFFICIENCY FIX: Non-blocking threadpool offloaded execution
    # Fetch top 50 chunks for full checklist generation instead of 5
    fetch_amount = 50 if is_checklist else 5
    results, context_string = await run_in_threadpool(
        retrieve_and_format, request.query, request.domain, top_k=fetch_amount, user_id=request.user_id
    )

    if not results or not context_string:
        return {"response": "No relevant context found in documents. Please ensure valid governance documents are uploaded and indexed."}

    if is_checklist:
        checklist_items = await run_in_threadpool(generate_checklist, context_string, results)
        if not checklist_items:
            return {"response": "Failed to generate structured checklist from the context.", "raw_data": None}

        # Format the JSON items into a beautiful markdown string for Streamlit UI
        from storage.db import save_checklist
        save_checklist(request.query, checklist_items, request.user_id)

        md_lines = ["### Compliance Extraction Request\n"]
        for it in checklist_items:
            md_lines.append(f"- **Domain:** {it.get('domain', 'general').capitalize()}\n  **Requirement:** {it.get('item', '')}")
            if it.get("source_section") and it.get("source_section") not in ["—", "â€”"]:  
                md_lines.append(f"  *(Source Section: {it['source_section']})*")

        answer_string = "\n".join(md_lines)
        return {"response": answer_string, "raw_data": checklist_items}
    else:
        # Otherwise, use standard Chat Q&A
        answer_string = await run_in_threadpool(generate_answer, request.query, context_string)
        return {"response": answer_string, "raw_data": None}

@app.post("/api/chat/stream")
async def chat_endpoint_stream(request: ChatRequest):
    from retrieval.retriever import retrieve_and_format
    from llm.generator import stream_answer
    from fastapi.responses import StreamingResponse

    # EFFICIENCY FIX: Non-blocking threadpool offloaded execution
    results, context_string = await run_in_threadpool(
        retrieve_and_format, request.query, request.domain, top_k=5, user_id=request.user_id
    )

    if not results or not context_string:
        async def mock_stream():
            yield "No relevant context found in documents. Please ensure valid governance documents are uploaded and indexed."
        return StreamingResponse(mock_stream(), media_type="text/plain")

    # Use standard Chat Q&A via stream
    generator = stream_answer(request.query, context_string)
    
    async def generate():
        for chunk in generator:
            yield chunk

    return StreamingResponse(generate(), media_type="text/event-stream")

# Mount the custom HTML UI
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

