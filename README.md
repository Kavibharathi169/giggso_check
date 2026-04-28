# GovCheck AI — Governance document to checklist

GovCheck ingests governance and compliance documents (PDF, Word, Excel, CSV, text, and web URLs), chunks and embeds them, and produces structured checklist items using a **hybrid RAG** stack (ChromaDB dense search + BM25). Data is scoped by `user_id` so sessions stay isolated in the vector store and BM25 corpus.

---

## Architecture

| Layer | Role |
|--------|------|
| **FastAPI (`main.py`)** | REST API: upload jobs, status polling, chat/stream. Serves the static web UI from `frontend/` at `/`. Enqueues ingestion jobs to Celery. |
| **Celery Worker (`queue_tasks.py`)** | Production job worker for ingestion with retries/backoff/time limits. |
| **Redis** | Celery broker/result backend and durable job-status store for `/api/status/{job_id}` polling. |
| **Streamlit (`app.py`)** | Optional dashboard: upload/poll, checklist table, domain filters, CSV/JSON/Excel export, RAG chat tab. Calls the API via `API_URL` (default `http://localhost:8000`). |
| **Ingestion** | `ingestion/router.py` routes by file type or URL to loaders (PDF, DOCX, XLSX, CSV, scrape, etc.). |
| **Chunking** | `chunking/chunker.py` uses **embedding-based semantic chunking** (paragraph units + cosine similarity boundaries) with a safe fallback to `RecursiveCharacterTextSplitter`; token sizing uses **tiktoken** (fallback if unavailable). Default chunk budget aligns with **multilingual-e5** (~512 tokens). |
| **Classification** | `classification/rule_classifier.py`: keyword rules first; optional **Groq** per-chunk fallback when `CLASSIFY_USE_LLM=true` (default is off for speed). |
| **Embeddings** | `embedding/embedder.py`: **sentence-transformers** (default `intfloat/multilingual-e5-base`), `passage:` / `query:` prefixes for E5. |
| **Stores** | **ChromaDB** (`vectorstore/chroma_store.py`) + **BM25** (`retrieval/bm25_store.py` via `rank-bm25`), per-user on disk under `OUTPUT_DIR`. |
| **LLM** | **Groq** (`llm/`) for checklist JSON and Q&A; prompts stress grounding in retrieved context. |

---

## Project layout

```
├── main.py              # FastAPI app, CORS, static frontend mount
├── app.py               # Streamlit UI
├── requirements.txt
├── docker-compose.yml
├── Dockerfile
├── .env.example         # Copy to .env and set secrets
├── frontend/            # Static HTML/JS UI (served at http://localhost:8000/)
├── storage/db.py        # SQLite checklist history (SQLAlchemy)
├── ingestion/           # Loaders + router
├── chunking/            # chunker.py, token_utils.py
├── classification/      # rule_classifier.py, llm_classifier.py
├── embedding/           # embedder.py
├── vectorstore/         # chroma_store.py
├── retrieval/           # retriever.py, bm25_store.py
└── llm/                 # groq_client, generator, prompt_templates
```

---

## API (localhost:8000)

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/upload` | `multipart/form-data`: `file` and/or `link`, `user_id`. Returns `job_id`. |
| GET | `/api/status/{job_id}` | `status`, `progress`, `message` (`completed` / `error`). |
| POST | `/api/chat` | JSON: `query`, `domain`, `user_id`. Retrieval + Groq; checklist-style queries return `raw_data` JSON. |
| POST | `/api/chat/stream` | Streaming text response for normal Q&A. |

Interactive docs: **http://127.0.0.1:8000/docs**

---

## Setup

### 1. Environment

Copy `.env.example` to `.env` and set at least:

```env
GROQ_API_KEY=your_key_here
GROQ_GENERATOR_MODEL=llama-3.3-70b-versatile
EMBEDDING_MODEL=intfloat/multilingual-e5-base
CHROMA_PERSIST_DIR=./chroma_db
OUTPUT_DIR=./output
```

Optional tuning (see code / comments in repo):

```env
API_URL=http://localhost:8000          # Streamlit → API
CLASSIFY_USE_LLM=false                  # true = Groq per chunk when rules miss (slower)
CLASSIFY_DEFAULT_DOMAIN=audit_compliance
CHUNK_MAX_TOKENS=512
CHUNK_OVERLAP=128
SEMANTIC_SIM_THRESHOLD=0.70
SEMANTIC_MIN_TOKENS=128
VERIFY_ENABLE=true
VERIFY_MIN_CONFIDENCE=0.80
RERANK_ENABLE=false
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
RERANK_CANDIDATE_MULTIPLIER=2
RETRIEVAL_FETCH_MULTIPLIER=3
EMBEDDING_BATCH_SIZE=192
TORCH_NUM_THREADS=8                     # CPU only, optional
SAVE_CHUNK_JSONL=false                  # true = append chunks to output/chunked.jsonl
REDIS_URL=redis://127.0.0.1:6379/0
CELERY_RESULT_BACKEND=redis://127.0.0.1:6379/0
JOB_STATUS_TTL_SEC=86400
CELERY_TASK_SOFT_TIME_LIMIT_SEC=1500
CELERY_TASK_TIME_LIMIT_SEC=1800
MAX_UPLOAD_MB=50
UPLOAD_CHUNK_SIZE_BYTES=1048576
LOCAL_JOB_STATUS_TTL_SEC=3600
LOCAL_JOB_STATUS_MAX_ITEMS=2000
MAX_INGESTION_CHUNKS=5000
```

### 2. Install dependencies

```bash
python -m venv .venv
```

**Windows (PowerShell):**

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**

```bash
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` includes **FastAPI**, **chromadb**, **sentence-transformers**, **streamlit**, **rank-bm25**, **groq**, and ingestion libraries. First embedding model load may download weights from Hugging Face.

### 3. Run (three terminals)

**Terminal 1 — API**

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

**Terminal 2 — Celery worker**

```bash
celery -A celery_app.celery_app worker --loglevel=info --concurrency=2
```

**Terminal 3 — Streamlit (optional)**

```bash
streamlit run app.py --server.port 8501 --server.address 127.0.0.1
```

- **Streamlit:** http://127.0.0.1:8501  
- **Static UI + API:** http://127.0.0.1:8000  

Keep Redis, the API, and worker running whenever you ingest documents.

### 4. Docker

```bash
docker-compose up --build -d
```

Adjust ports and commands in `docker-compose.yml` / `Dockerfile` if you override defaults.

---

## Using the app

### Streamlit (`app.py`)

1. **Sidebar:** Upload a file or paste a URL, then **Process documents**. The app polls `/api/status/{job_id}` until completion, then calls `/api/chat` to build the checklist.
2. **Filter by domain:** Sidebar domain buttons narrow the checklist table.
3. **Start Over:** Clears session state (sidebar **Session** section and/or **Checklist** tab). Use this before a new document for a clean session.
4. **Checklist tab:** **CSV** export uses fixed columns (`requirement`, `domain`, `source_section`, `priority`, `action_type`, `evidence_required`, `chunk_id`, `source_url`, etc.). **JSON** / **Excel** export full row payloads.
5. **RAG Chat tab:** Questions go to `/api/chat/stream` (or `/api/chat` for checklist-style phrasing).

### Static frontend (`frontend/index.html`)

1. **Local File** / **Cloud Link** tabs; upload or **Analyze** on URL.
2. **Export CSV / JSON**, **Start Over** (resets UI, new anonymous `user_id`, cleared checklist and chat).
3. **AI Assistant** floating button: chat against indexed content for that browser session’s `user_id`.

---

## Troubleshooting

| Issue | What to check |
|--------|----------------|
| `No module named 'rank_bm25'` | `pip install rank-bm25` (listed in `requirements.txt`). |
| Ingestion errors | `GROQ_API_KEY`, disk space, `CHROMA_PERSIST_DIR` / `OUTPUT_DIR` writable. |
| Empty checklist | Model/key errors; ensure upload completed (`status` = `completed`) and `user_id` matches between upload and chat. |
| Port already in use | Change `--port` for uvicorn or Streamlit, or stop the old process. |

---

## License / compliance

Use in line with your organization’s policies and the terms of Groq, Hugging Face models, and third-party document sources.

---

## Deploy on Render

This repo includes a Render blueprint at `render.yaml`.

### Recommended deployment mode (current codebase)

Deploy as a **single web service** running FastAPI (`main.py`).
This is recommended because uploads are written to local disk and then processed in background. On Render, separate web and worker services do not share local filesystem by default.

The app is already resilient: if Celery/Redis is unavailable, `/api/upload` automatically falls back to local background processing in the same service.

### Steps

1. Push this repo (with `render.yaml`) to GitHub.
2. In Render, choose **New +** -> **Blueprint**.
3. Select your repo and create the service.
4. In Render service settings, set:
   - `GROQ_API_KEY` (required secret)
   - any optional tuning vars you want from `.env.example`
5. Deploy.

After deploy:
- API docs: `https://<your-service>.onrender.com/docs`
- Static frontend: `https://<your-service>.onrender.com/`

### Notes

- First requests can be slow while embedding/model artifacts are downloaded.
- `CHROMA_PERSIST_DIR` and `OUTPUT_DIR` are configured to Render persistent disk (`/var/data/...`) in `render.yaml`.
- If you later want true distributed queue workers, switch uploads/storage to a shared object store (for example, S3) before splitting API and Celery into separate services.
